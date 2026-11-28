// RC3 compatibility candidate. Trusted server process only. No deployment, network
// endpoint, or host approval simulation. Never expose the owner interface as MCP tools.
import {beginReview} from '../base/owner-binding-rc2/owner-transport.mjs';
import {prepare,displayExact} from '../base/owner-ui-rc1/owner-review.mjs';
const uuid=/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/;
const plain=x=>x!==null&&typeof x==='object'&&Object.getPrototypeOf(x)===Object.prototype&&Object.values(Object.getOwnPropertyDescriptors(x)).every(d=>Object.hasOwn(d,'value'));
const keys=(v,allowed)=>plain(v)&&Object.keys(v).every(k=>allowed.includes(k));
const fail=code=>{throw Error(code);};
const opNames={keenetic:{exec_command:'exec',write_file:'write_file',queue_router_task:'legacy'},ha:{ha_exec_command:'exec',ha_write_file:'write_file'}};
const statuses=['queued','running','done','failed','unknown','unknown_submission','denied','not_found'];
const outputSchema={type:'object',properties:{status:{type:'string',enum:statuses},request_ref:{type:'string',format:'uuid'},job_id:{type:'string',format:'uuid'}},required:['status','request_ref'],additionalProperties:false};
const annotation=op=>({readOnlyHint:false,destructiveHint:true,idempotentHint:false,openWorldHint:op!=='write_file'});
const refSchema={type:'string',format:'uuid',description:'Non-secret reference for the exact operation approved separately in the owner portal. Not a permission or proof.'};
const execProps={command:{type:'string',minLength:1,maxLength:4096},timeout:{type:'integer',minimum:1,maximum:180,default:20}};
const writeProps={path:{type:'string',pattern:'^/',maxLength:512},content:{type:'string',maxLength:40000}};
const confirm={type:'boolean',description:'Optional legacy assertion; never grants authorization. False denies the operation.'};
export function descriptors(target,schemes){
 if(!Object.hasOwn(opNames,target)||!Array.isArray(schemes)||!schemes.length||schemes.some(x=>x.type!=='oauth2'||!Array.isArray(x.scopes)||!x.scopes.length||x.scopes.some(s=>typeof s!=='string'||!s)))fail('verified_oauth_scheme_required');
 const writes=Object.entries(opNames[target]).map(([name,op])=>{
  const props=op==='exec'?execProps:op==='write_file'?writeProps:{op:{type:'string',enum:['exec','write_file']},...execProps,...writeProps};
  return {name,description:'Submit only the exact separately owner-approved operation via the normal authenticated MCP invocation. Review all arguments and obtain explicit consent. Never retry a denial or unknown submission.',inputSchema:{type:'object',properties:{...props,request_ref:refSchema,confirmed:confirm},required:[...(op==='exec'?['command']:op==='write_file'?['path','content']:['op']),'request_ref'],additionalProperties:false},outputSchema,annotations:annotation(op),securitySchemes:structuredClone(schemes),_meta:{securitySchemes:structuredClone(schemes)}};
 });
 return [...writes,{name:target==='ha'?'ha_get_operation_status':'get_operation_status',description:'Read the result of a previously submitted operation by its non-secret reference. Never submits or retries work.',inputSchema:{type:'object',properties:{request_ref:refSchema},required:['request_ref'],additionalProperties:false},outputSchema,annotations:{readOnlyHint:true,destructiveHint:false,idempotentHint:true,openWorldHint:false},securitySchemes:structuredClone(schemes),_meta:{securitySchemes:structuredClone(schemes)}}];
}
function normalized(target,name,args){
 const op=opNames[target]?.[name];if(!op||!plain(args)||!uuid.test(args.request_ref??'')||(Object.hasOwn(args,'confirmed')&&args.confirmed!==true))fail('invalid_invocation');
 const route=op==='legacy'?'legacy':'named',kind=op==='legacy'?args.op:op;
 if(!['write_file','exec'].includes(kind))fail('unsupported_operation');
 const permitted=['request_ref','confirmed',...(route==='legacy'?['op']:[]),...(kind==='exec'?['command','timeout']:['path','content'])];
 if(!keys(args,permitted))fail('invalid_invocation');
 const {request_ref,confirmed,op:ignored,...fields}=args;
 return prepare(target,route,{op:kind,...fields});
}
// verifyClient/verifyOwner are trusted, independently implemented authentication
// boundaries. They must validate actual server-side sessions/tokens, issuer,
// audience, client_id, subject, expiry and scopes; never accept claims from tool
// arguments, arbitrary headers, or the model. The adapter does not attest a
// ChatGPT confirmation dialog. A genuine host MCP request is still mandatory.
function validIdentity(v){return plain(v)&&['issuer','audience','subject','clientId','binding'].every(k=>typeof v[k]==='string'&&v[k].length>0&&v[k].length<=512)&&Array.isArray(v.scopes)&&v.scopes.every(s=>typeof s==='string');}
const identity=v=>JSON.stringify([v.issuer,v.audience,v.subject,v.clientId,v.binding]);
// Owner portal supplies an independently paired client identity from its authenticated registry.
// This object is intentionally separate from the model-callable interface.
export function createAdapter({target,transport,verifyClient,verifyOwner,resolvePairedClient,lookupRequest,recoveryStore,identityKey,requiredScope,clock=Date.now,maxPending=32}){
 if(!Object.hasOwn(opNames,target)||typeof verifyClient!=='function'||typeof verifyOwner!=='function'||typeof resolvePairedClient!=='function'||typeof lookupRequest!=='function'||!['begin','get','outcome'].every(k=>typeof recoveryStore?.[k]==='function')||!(identityKey instanceof Uint8Array)||identityKey.byteLength!==32||typeof requiredScope!=='string'||!requiredScope||!Number.isInteger(maxPending)||maxPending<1||maxPending>100)fail('invalid_adapter_configuration');
 const pending=new Map();
 const hmac=crypto.subtle.importKey('raw',new Uint8Array(identityKey),{name:'HMAC',hash:'SHA-256'},false,['sign']);
 const hashIdentity=async(role,v)=>Array.from(new Uint8Array(await crypto.subtle.sign('HMAC',await hmac,new TextEncoder().encode(JSON.stringify([target,role,identity(v)])))),b=>b.toString(16).padStart(2,'0')).join('');
 const ownerAuth=async ctx=>{const o=await verifyOwner(ctx);if(!validIdentity(o)||!o.scopes.includes('owner:consent'))fail('unauthorized_owner');return hashIdentity('owner',o);};
 const clientAuth=async ctx=>{const p=await verifyClient(ctx);if(!validIdentity(p)||!p.scopes.includes(requiredScope))fail('unauthorized_client');return hashIdentity('client',p);};
 const prune=()=>{for(const [k,v]of pending)if(clock()>=v.deadline&&!v.busy)pending.delete(k);};
 const record=(ref,owner)=>{if(!uuid.test(ref??''))fail('invalid_reference');const r=pending.get(ref);if(!r||r.owner!==owner)fail('unknown_reference');return r;};
 const visible=(ref,r)=>({request_ref:ref,status:r.state,expires_at:r.deadline,display:r.review.display(),client_key_sha256:r.review.pairing()?.client_key_sha256??null});
 const owner=Object.freeze({
  async prepare(ownerCtx,pairHandle,name,args){
   const ownerId=await ownerAuth(ownerCtx);const paired=await resolvePairedClient(ownerCtx,pairHandle);if(!validIdentity(paired)||!paired.scopes.includes(requiredScope))fail('unpaired_client');
   if(!plain(args)||Object.hasOwn(args,'request_ref'))fail('invalid_owner_arguments');
   const clientId=await hashIdentity('client',paired),ref=crypto.randomUUID();const snapshot=normalized(target,name,{...args,request_ref:ref});prune();if(pending.size>=maxPending)fail('pending_capacity');
   // Reserve synchronously before network/crypto awaits. No task logs or output to model.
   const started=clock(),r={owner:ownerId,client:clientId,name,snapshot,deadline:started+120000,state:'registering',busy:true};pending.set(ref,r);
   try{r.review=await beginReview(target,snapshot.route,snapshot.task,transport,clock);r.state=r.review.status();return visible(ref,r);}catch{r.state='unknown_registration';fail('registration_not_confirmed');}finally{r.busy=false;}
  },
  async approve(ownerCtx,ref,explicit,pairedFingerprint){
   const o=await ownerAuth(ownerCtx),r=record(ref,o);if(r.busy||r.state!=='review'||explicit!==true||clock()>=r.deadline)fail('approval_not_available');
   if(pairedFingerprint!==r.review.pairing()?.client_key_sha256)fail('pairing_mismatch');r.busy=true;r.state='approving';
   try{const x=await r.review.approve(true,pairedFingerprint);r.state=x.status;return {status:r.state};}finally{r.busy=false;}
  },
  async revoke(ownerCtx,ref){const o=await ownerAuth(ownerCtx),r=record(ref,o);if(r.busy||!['review','approved','unknown_approval','approval_denied','expired','storage_blocked'].includes(r.state))fail('not_revocable');r.busy=true;try{const x=await r.review.revoke();r.state=x.status;return {status:r.state};}finally{r.busy=false;}},
  // Read-only reconciliation is separate from resubmission. The caller must use
  // the existing authenticated GET /v1/requests/:key and NOT replay a tool call.
  async recoveryReference(ownerCtx,ref){const o=await ownerAuth(ownerCtx),r=recoveryStore.get(ref,target);if(!r||r.ownerHash!==o||!['queued','unknown_submission'].includes(r.outcome))fail('recovery_not_applicable');return {request_key:r.requestKey,status:r.outcome};}
 });
 const mcp=Object.freeze({
  async status(authenticatedIngress,args){
   const c=await clientAuth(authenticatedIngress);if(!keys(args,['request_ref'])||!uuid.test(args.request_ref??''))fail('invalid_reference');const r=recoveryStore.get(args.request_ref,target);
   if(!r||r.clientHash!==c||!['queued','unknown_submission'].includes(r.outcome))fail('unknown_reference');
   let v;try{v=await lookupRequest(r.requestKey);}catch{return {status:'unknown_submission',request_ref:args.request_ref};}
   if(v?.status==='not_found')return {status:'not_found',request_ref:args.request_ref};
   if(!uuid.test(v?.id??'')||!['queued','running','done','failed','unknown'].includes(v?.status))return {status:'unknown_submission',request_ref:args.request_ref};
   return {status:v.status,request_ref:args.request_ref,job_id:v.id};
  },
  async execute(authenticatedIngress,name,args){
   const c=await clientAuth(authenticatedIngress),actual=normalized(target,name,args),r=pending.get(args.request_ref);
   if(!r||r.client!==c||r.name!==name||r.busy||r.state!=='approved'||clock()>=r.deadline)fail('operation_not_approved');
   if(displayExact(actual)!==displayExact(r.snapshot))fail('operation_changed');
   r.busy=true;r.state='submitting';
   // Persist the reconciliation handle before any irreversible dispatch. If the
   // process dies after this transaction, the next instance can only read status;
   // the ephemeral private key and pending review are never persisted or replayed.
   try{recoveryStore.begin({ref:args.request_ref,target,requestKey:r.review.pairing().request_key,clientHash:r.client,ownerHash:r.owner,created:clock()});}catch{r.state='storage_blocked';r.busy=false;fail('recovery_store_unavailable');}
   try{const x=await r.review.sendAuthorizedInvocation(actual,transport.sendAuthorizedInvocation);r.state=x.status==='expired'?'denied':x.status;try{if(!recoveryStore.outcome(args.request_ref,target,r.state))r.state='unknown_submission';}catch{r.state='unknown_submission';}return {status:r.state,request_ref:args.request_ref};}catch{r.state='unknown_submission';return {status:r.state,request_ref:args.request_ref};}finally{r.busy=false;pending.delete(args.request_ref);}
  }
 });
 return Object.freeze({owner,mcp});
}
