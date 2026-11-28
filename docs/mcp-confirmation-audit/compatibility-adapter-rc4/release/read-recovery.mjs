// Read-only existing Worker recovery endpoint. Trusted process only.
const id=/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/;
export function readRecovery({origin,adminCredential,fetchImpl=globalThis.fetch}){
 const u=new URL(origin);if(u.protocol!=='https:'||u.username||u.password||u.href!==u.origin+'/')throw Error('invalid_pinned_origin');
 if(typeof adminCredential!=='string'||adminCredential.length<32||adminCredential.length>4096||/[\x00-\x20\x7f]/.test(adminCredential))throw Error('invalid_local_credential');
 return async requestKey=>{
  if(!id.test(requestKey??''))throw Error('invalid_request_key');
  const r=await fetchImpl(u.origin+'/v1/requests/'+requestKey,{method:'GET',headers:{authorization:'Bearer '+adminCredential},cache:'no-store',credentials:'omit',redirect:'error',signal:AbortSignal.timeout(10000)});
  if(r.redirected||r.status>=300&&r.status<400)throw Error('unexpected_redirect');
  if(r.status===404){await r.body?.cancel();return {status:'not_found'};}
  if(r.status!==200){await r.body?.cancel();throw Error('recovery_unavailable');}
  const reader=r.body?.getReader();if(!reader)throw Error('invalid_response');let bytes=0,data='';const decoder=new TextDecoder();
  try{for(;;){const x=await reader.read();if(x.done)break;if((bytes+=x.value.length)>8192){await reader.cancel();throw Error('response_too_large');}data+=decoder.decode(x.value,{stream:true});}data+=decoder.decode();}finally{reader.releaseLock();}
  let v;try{v=JSON.parse(data);}catch{throw Error('invalid_response');}
  if(!id.test(v?.id??'')||!['queued','running','done','failed','unknown'].includes(v?.status))throw Error('invalid_recovery_result');
  return {id:v.id,status:v.status};
 };
}
