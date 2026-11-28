// Owner-local trusted process only. NEVER expose as a model-callable tool.
// This wrapper is not a host approval attestation and cannot replace ChatGPT's prompt.
const id=/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/;
const proof=/^[a-f0-9]{128}$/;
const keys=/^[a-f0-9]{64}$/;
const allowedErrors=new Set(['pending_not_revocable','pending_not_approvable','remote_disabled','scope_denied','confirmation_required','pending_client_proof_required','invalid_confirmation_argument','invalid_pending_request','pending_conflict','pending_capacity','invalid_client_proof','unauthorized']);
function secret(s){if(typeof s!=='string'||s.length<32||s.length>4096||/[\x00-\x20\x7f]/.test(s))throw Error('invalid_local_credential');return s;}
export function trustedTransport({target,origin,adminCredential,policyCredential,fetchImpl=globalThis.fetch}){
 if(!['keenetic','ha'].includes(target))throw Error('invalid_target');
 const u=new URL(origin);if(u.protocol!=='https:'||u.username||u.password||u.href!==u.origin+'/')throw Error('invalid_pinned_origin');
 const pinned=u.origin, admin=secret(adminCredential),policy=secret(policyCredential);if(admin===policy)throw Error('credentials_must_differ');
 const used=new Set();
 // No configurable URL at invocation time, no redirects, no fallback channel, no retries.
 async function request(path,body,owner=false,extra={}){
  const r=await fetchImpl(pinned+path,{method:'POST',headers:{authorization:'Bearer '+admin,'content-type':'application/json',...(owner?{'x-control-policy-token':policy}:{}),...extra},body:JSON.stringify(body),redirect:'error',cache:'no-store',credentials:'omit',signal:AbortSignal.timeout(10000)});
  if(r.redirected||r.status>=300&&r.status<400)throw Error('unexpected_redirect');
  const reader=r.body?.getReader();if(!reader)throw Error('invalid_response');let size=0;let data='';const decoder=new TextDecoder();
  try{for(;;){const x=await reader.read();if(x.done)break;if((size+=x.value.length)>65536){await reader.cancel();throw Error('response_too_large');}data+=decoder.decode(x.value,{stream:true});}data+=decoder.decode();}finally{reader.releaseLock();}
  try{return {status:r.status,value:JSON.parse(data)};}catch{throw Error('invalid_response');}
 }
 function result(v,allowed){if(v&&typeof v==='object'&&allowed.includes(v.status))return {status:v.status};return allowedErrors.has(v?.error)?{error:v.error}:{error:'unknown_result'};}
 const ownerChannel=Object.freeze({
  async approve(b){if(b?.confirmed!==true)throw Error('explicit_owner_action_required');const {status,value}=await request('/v1/owner/approve-operation',b,true);return status===200?result(value,['approved']):result(value,[]);},
  async revoke(b){const {status,value}=await request('/v1/owner/revoke-operation',b,true);return status===200?result(value,['revoked']):result(value,[]);}
 });
 const clientChannel=Object.freeze({
  async register(b){const {status,value}=await request('/v1/operation-pending',b);if(status!==201||!id.test(value?.request_key??'')||!id.test(value?.challenge??'')||!keys.test(value?.client_key_sha256??'')||value.expires_in!==120)throw Error('registration_not_confirmed');return {request_key:value.request_key,challenge:value.challenge,client_key_sha256:value.client_key_sha256,expires_in:120};},
  // In a real plugin this method must be reachable ONLY from the trusted host-authorized invocation dispatcher.
  // No model-supplied host_approved flag, no direct fallback after MCP denial, no owner credentials on this call.
  async sendAuthorizedInvocation(envelope){
   const {path,headers,body}=envelope??{};const k=headers?.['Idempotency-Key'],p=headers?.['X-Operation-Proof'];
   if(!id.test(k??'')||!proof.test(p??'')||Object.keys(headers).length!==2||used.has(k))throw Error('invalid_or_used_invocation');
   if(path==='/mcp'){
    const allowed=target==='ha'?['ha_write_file','ha_exec_command']:['write_file','exec_command','queue_router_task'];
    if(body?.method!=='tools/call'||!allowed.includes(body.params?.name)||body.params?.arguments?.confirmed!==true)throw Error('invalid_invocation');
   }else if(path==='/v1/jobs'){if(!['write_file','exec'].includes(body?.op)||body.confirmed!==true)throw Error('invalid_invocation');}else throw Error('invalid_invocation');
   // Fail closed after a bounded number of invocations; restart only in an owner-controlled maintenance workflow.
   if(used.size>=1000)throw Error('local_invocation_capacity');used.add(k);
   const {status,value}=await request(path,body,false,{'Idempotency-Key':k,'X-Operation-Proof':p});
   const v=path==='/mcp'?value?.result?.structuredContent:value;
   if((path==='/mcp'?status===200:status===202)&&v?.status==='queued')return {status:'queued'};
   if(allowedErrors.has(v?.error))return {status:'denied',error:v.error};return {status:'unknown_submission'};
  }
 });
 return Object.freeze({clientChannel,ownerChannel});
}
