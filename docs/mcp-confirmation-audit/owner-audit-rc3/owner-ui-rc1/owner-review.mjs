// Isolated owner UI/client adapter; no network, token store, or host approval API.
// A trusted transport is injected by an authenticated client. Never use as a
// fallback after a host denial. This does not attest ChatGPT approval.
const routes = new Set(['named','legacy','direct']);
const devices = new Set(['keenetic','ha']);
const modes = new Set(['0600','0640','0644','0700','0755']);
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const fail = code => {throw new Error(code);};
const plain = v => v!==null && typeof v==='object' && Object.getPrototypeOf(v)===Object.prototype && Object.values(Object.getOwnPropertyDescriptors(v)).every(d=>Object.hasOwn(d,'value'));
const exact = (v,keys) => Object.keys(v).every(k=>keys.includes(k));
const bytes = s=>new TextEncoder().encode(s).length;
export function prepare(target, route, input){
  if(!devices.has(target)||!routes.has(route)|| (target==='ha'&&route==='legacy') || !plain(input))fail('invalid_target_or_task');
  const op=input.op;
  if(!['write_file','exec'].includes(op))fail('unsupported_operation');
  const timeout=Object.hasOwn(input,'timeout')?input.timeout:20;
  if(!Number.isInteger(timeout)||timeout<1||timeout>(op==='exec'?180:45))fail('invalid_timeout');
  let task;
  if(op==='write_file'){
    if(!exact(input,['op','path','content','mode','timeout'])||typeof input.path!=='string'||!input.path.startsWith('/')||input.path.length>512||input.path.includes('\0')||input.path.split('/').some(v=>v==='.'||v==='..')||typeof input.content!=='string'||bytes(input.content)>40000|| (Object.hasOwn(input,'mode')&&!modes.has(input.mode)))fail('invalid_write');
    // Named tool does not expose mode or timeout. Legacy schema must be scanned
    // before enabling non-default write options; fail closed here too.
    if(route!=='direct'&&(timeout!==20||Object.hasOwn(input,'mode')))fail('unsupported_write_options');
    task={op,path:input.path,content:input.content,...(Object.hasOwn(input,'mode')?{mode:input.mode}:{}),timeout};
  }else{
    if(!exact(input,['op','command','timeout'])||typeof input.command!=='string'||!input.command.trim()||input.command.length>4096||input.command.includes('\0'))fail('invalid_exec');
    task={op,command:input.command,timeout};
  }
  return Object.freeze({target,route,task:Object.freeze(task)});
}
export function displayExact(p){
  // Render as text, not markup. Escape bidi, invisible format characters,
  // control chars, and non-ASCII so the displayed task is unambiguous.
  return JSON.stringify({target:p.target,route:p.route,task:p.task},null,2).replace(/[^\x20-\x7e\n]/g,c=>'\\u'+c.charCodeAt(0).toString(16).padStart(4,'0'));
}
function envelope(p,capability){
  const {task:t,target,route}=p;
  const authorization={confirmed:true,approval_id:capability};
  const requestKey=crypto.randomUUID();
  const headers={'Idempotency-Key':requestKey};
  if(route==='direct')return {path:'/v1/jobs',headers,body:{...t,...authorization}};
  const {op,...args}=t;
  if(op==='write_file')delete args.timeout;
  return {path:'/mcp',headers,body:{jsonrpc:'2.0',id:crypto.randomUUID(),method:'tools/call',params:{name:route==='legacy'?'queue_router_task':(target==='ha'?'ha_':'')+(op==='exec'?'exec_command':'write_file'),arguments:{...(route==='legacy'?{op}:{}),...args,...authorization}}}};
}
// The pending object must be the same object held by the intended trusted
// client. This is an in-process guard only, NOT remote principal binding.
// Host approvals and authenticated transport are separate integration gates.
export function ownerReview(pending,{requestApproval,now=Date.now}){
  const snapshot=prepare(pending.target,pending.route,pending.task);
  let state='review',cap=null,deadline=0;
  function clear(next){cap=null;state=next;}
  return Object.freeze({snapshot,status:()=>state,display:()=>displayExact(snapshot),
    cancel(){if(['review','approving','approved'].includes(state))clear('cancelled');},
    hostDenied(clientPending){if(clientPending!==pending||state!=='approved')fail('pending_client_not_authorized');clear('denied');},
    async approve(explicit){
      if(state!=='review'||explicit!==true)fail('explicit_owner_action_required');
      state='approving';const started=now();
      let answer;
      try{answer=await requestApproval(snapshot.target,{...snapshot.task,confirmed:true});}catch{if(state==='approving')clear('unknown_approval');return {status:state};}
      if(state!=='approving')return {status:state};
      if(!plain(answer)||typeof answer.approval_id!=='string'||!uuid.test(answer.approval_id)||answer.expires_in!==120){clear('approval_failed');return {status:state};}
      deadline=started+120000;
      if(now()>=deadline){clear('expired');return {status:state};}
      cap=answer.approval_id;state='approved';return {status:state};
    },
    // Only the intended local client may use this one-shot method. Its
    // real host confirmation is checked by the host, never inferred here.
    // Denials/uncertain outcomes are terminal and never cause a retry.
    async deliverTo(clientPending,sendOnce){
      if(clientPending!==pending||state!=='approved'||typeof sendOnce!=='function')fail('pending_client_not_authorized');
      let current;
      try{current=prepare(clientPending.target,clientPending.route,clientPending.task);}catch{clear('cancelled');fail('pending_task_changed');}
      if(displayExact(current)!==displayExact(snapshot)){clear('cancelled');fail('pending_task_changed');}
      if(now()>=deadline){clear('expired');return {status:state};}
      const request=envelope(snapshot,cap);clear('submitting');
      try{
        const result=await sendOnce(request);
        if(result?.status==='queued'){clear('queued');return {status:state};}
        if(result?.status==='denied'){clear('denied');return {status:state};}
        clear('unknown_submission');return {status:state};
      }catch{clear('unknown_submission');return {status:state};}
    }
  });
}
