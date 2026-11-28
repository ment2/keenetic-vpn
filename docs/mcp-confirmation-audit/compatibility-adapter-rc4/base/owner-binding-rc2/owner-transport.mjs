// RC2 trusted adapter only. Import RC1 UI validation from the pinned parent folder.
// This object MUST NOT be registered as a model-callable tool. It never asserts
// that ChatGPT approved a request; the actual host-authorized invocation is a
// precondition of the injected transport's send operation.
import {prepare,displayExact} from '../owner-ui-rc1/owner-review.mjs';
import {createClientProof,validId} from './pending-consent.mjs';
export async function beginReview(target,route,input,transport,clock=Date.now){
 const snapshot=prepare(target,route,input);
 const started=clock(),client=await createClientProof(target,snapshot.task);
 let state='registering',review=null,deadline=started+120000;
 // Transport is trusted, pinned to this worker and independently authenticated.
 // It returns parsed allowlisted response fields, no credentials or headers.
 try{
  const r=await transport.register(client.registration);
  if(r?.request_key!==client.registration.request_key||!validId(r.challenge)||r.expires_in!==120)throw Error('registration_invalid');
  review=client.ownerReview(r.challenge);
  if(r.client_key_sha256!==review.client_key_sha256)throw Error('client_binding_mismatch');
  state=clock()<deadline?'review':'expired';
 }catch{state='unknown_registration';}
 function approvalBody(){return {...review,confirmed:true};}
 function revokeBody(){const {request_key,client_key_sha256,challenge}=review;return {request_key,client_key_sha256,challenge};}
 async function revoke(){
  if(!['review','approving','approved','expired','unknown_approval','approval_denied'].includes(state)||!review)return {status:state};
  state='revoking';
  try{const r=await transport.revoke(revokeBody());state=r?.status==='revoked'?'revoked':r?.error==='pending_not_revocable'?'not_revocable':'unknown_revoke';}catch{state='unknown_revoke';}
  return {status:state};
 }
 return Object.freeze({snapshot,status:()=>state,display:()=>displayExact(snapshot),
  // Public fingerprint and challenge are pairing data, not approval capability.
  // The trusted owner UI must independently match this fingerprint to the intended
  // client channel, not accept an untrusted label or value copied from chat.
  pairing:()=>review?Object.freeze({request_key:review.request_key,client_key_sha256:review.client_key_sha256,challenge:review.challenge}):null,
  async approve(explicit,pairedKey){
   if(state!=='review'||explicit!==true||pairedKey!==review.client_key_sha256)throw Error('explicit_paired_owner_action_required');
   if(clock()>=deadline){state='expired';return {status:state};}
   state='approving';
   try{const r=await transport.approve(approvalBody());if(state==='approving')state=r?.status==='approved'?'approved':'approval_denied';}catch{if(state==='approving')state='unknown_approval';}
   return {status:state};
  },revoke,
  // Call ONLY from the trusted transport path following a genuine host-authorized
  // invocation of the selected MCP tool. Do not expose a caller-supplied host
  // confirmation boolean. The host pipeline cannot yet be attested in this RC.
  async sendAuthorizedInvocation(current,sendOnce){
   if(state!=='approved'||typeof sendOnce!=='function')throw Error('not_approved');
   let actual;try{actual=prepare(current.target,current.route,current.task);}catch{await revoke();throw Error('operation_changed');}
   if(displayExact(actual)!==displayExact(snapshot)){await revoke();throw Error('operation_changed');}
   if(clock()>=deadline){state='expired';return {status:state};}
   state='submitting';
   try{
    const headers=await client.headersOnce(review.challenge);
    const {op,...args}=snapshot.task;
    if(snapshot.route!=='direct'&&op==='write_file')delete args.timeout;
    const body=snapshot.route==='direct'?{...snapshot.task,confirmed:true}:{jsonrpc:'2.0',id:crypto.randomUUID(),method:'tools/call',params:{name:snapshot.route==='legacy'?'queue_router_task':(target==='ha'?'ha_':'')+(op==='write_file'?'write_file':'exec_command'),arguments:{...(snapshot.route==='legacy'?{op}:{}),...args,confirmed:true}}};
    const r=await sendOnce({path:snapshot.route==='direct'?'/v1/jobs':'/mcp',headers,body});
    state=r?.status==='queued'?'queued':r?.status==='denied'?'denied':'unknown_submission';
   }catch{state='unknown_submission';}
   return {status:state};
  }
 });
}
