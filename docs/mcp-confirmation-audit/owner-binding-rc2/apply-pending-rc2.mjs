// Apply to *disposable copies* already transformed by the exact RC1 overlay.
// This generator does not contact a server or deploy. Expected SHA-256 values
// must come from the trusted isolated build, never from an unknown live file.
import {readFileSync,writeFileSync,copyFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {dirname,join} from 'node:path';
const [target,entry,coord,entryHash,coordHash]=process.argv.slice(2);
if(!['keenetic','ha'].includes(target)||!entry||!coord||(target==='ha')!==(entry===coord))throw Error('usage: keenetic|ha entry coordinator entrySHA coordinatorSHA');
const sha=s=>createHash('sha256').update(s).digest('hex');
function readChecked(p,h){const b=readFileSync(p);if(!/^[a-f0-9]{64}$/.test(h??'')||sha(b)!==h)throw Error('baseline hash mismatch');return b.toString('utf8');}
function one(s,a,b){if(s.split(a).length!==2)throw Error('unexpected anchor: '+a.slice(0,100));return s.replace(a,b);}
let outer=readChecked(entry,entryHash),inner=readChecked(coord,coordHash);
const imported="import {approveShape,pendingShape,revokeShape,verifyProof,createPendingTable,registerPending,approvePending,revokePending,checkPendingProof,pendingAuthorized,consumePending,clientKeyHash} from './pending-consent.mjs';\n";
inner=one(inner,'createConsentTables(this.sql);','createConsentTables(this.sql);createPendingTable(this.sql);');
const start=inner.indexOf("if(path==='/approve-operation'&&request.method==='POST'){");
const end=inner.indexOf("if(path==='/enqueue'&&request.method==='POST'){",start);
if(start<0||end<=start||inner.slice(start,end).split("INSERT INTO exact_consent").length!==2)throw Error('old approval block not found');
inner=inner.slice(0,start)+`if(['/operation-pending','/approve-operation','/revoke-operation'].includes(path)&&request.method==='POST'){
    let b;try{b=await body(request);}catch{return response({error:'invalid_pending_request'},400);}
    const registration=path==='/operation-pending',revoking=path==='/revoke-operation';
    if(!(registration?pendingShape(b):revoking?revokeShape(b):approveShape(b)))return response({error:'invalid_pending_request'},400);
    if(revoking)return this.tx(()=>revokePending(this.sql,{id:b.request_key,keyHash:b.client_key_sha256,challenge:b.challenge,now:Date.now()})?response({status:'revoked'}):response({error:'pending_not_revocable'},409));
    let task;
    try{
     const input=b.task;
     if(!input||typeof input!=='object'||Array.isArray(input)||!['exec','write_file'].includes(input.op)||!Object.hasOwn(input,'timeout'))throw Error('invalid_task');
     const keys=input.op==='exec'?['op','command','timeout']:['op','path','content','mode','timeout'];
     if(Object.keys(input).some(k=>!keys.includes(k)))throw Error('invalid_task');
     task=taskFromBody(input);
     if(task.op==='write_file')task.content_sha256=await contentHash(task.content);
    }catch{return response({error:'invalid_task'},400);}
    const fp=await digest(task);
    let keyHash=b.client_key_sha256;
    if(registration){
     if(!await verifyProof('${target}','register',b.request_key,fp,b.public_key,b.registration_proof))return response({error:'invalid_client_proof'},403);
     keyHash=await clientKeyHash(b.public_key);
    }
    return this.tx(()=>{
     const p=this.policy(),current=Date.now();
     if(!p.enabled)return response({error:'remote_disabled'},403);
     if(!p.scopes.includes(task.op))return response({error:'scope_denied'},403);
     if(registration){
      const registered=registerPending(this.sql,{id:b.request_key,digest:fp,publicKey:b.public_key,keyHash,revision:p.revision,now:current});
      if(typeof registered==='string')return response({error:registered},registered==='pending_capacity'?503:409);
      return response({request_key:b.request_key,client_key_sha256:keyHash,challenge:registered.challenge,expires_in:120},201);
     }
     const denied=mutationDenial(p,task,b);
     if(denied)return response({error:denied},403);
     return approvePending(this.sql,{id:b.request_key,digest:fp,keyHash,challenge:b.challenge,revision:p.revision,now:current})?response({status:'approved'}):response({error:'pending_not_approvable'},409);
    });
   }
   `+inner.slice(end);
inner=one(inner,"const fingerprint=await digest(task),id=crypto.randomUUID(),encrypted=await seal(task,this.env.CONTROL_DATA_KEY,'task:'+id);\n    return this.tx(()=>{",`const fingerprint=await digest(task),id=crypto.randomUUID(),encrypted=await seal(task,this.env.CONTROL_DATA_KEY,'task:'+id);
    const checked=isMutation(task.op)?await checkPendingProof(this.sql,{target:'${target}',id:requestKey,digest:fingerprint,proof:b.client_proof}):null;
    return this.tx(()=>{`);
inner=one(inner,"if(previous)return previous.fingerprint===fingerprint?response({id:previous.id,status:previous.state,op:task.op,already_received:true}):response({error:'idempotency_conflict'},409);",`if(previous){
      if(isMutation(task.op)&&!pendingAuthorized(this.sql,checked,p.revision,Date.now(),true))return finish({error:'pending_client_proof_required'},403);
      return previous.fingerprint===fingerprint?finish({id:previous.id,status:previous.state,op:task.op,already_received:true}):finish({error:'idempotency_conflict'},409);
     }`);
inner=one(inner,"if(isMutation(task.op)&&!consumeApproval(this.sql,b.task.approval_id,fingerprint,p.revision,Date.now()))\n      return finish({error:'exact_operation_approval_required'},403);",`if(isMutation(task.op)&&!consumePending(this.sql,checked,p.revision,Date.now()))
      return finish({error:'pending_client_proof_required'},403);`);
// Nonmutating requests must never consume the pending mutation key or create a
// competing job on it, even if an authenticated caller knows the key.
inner=one(inner,"const previous=this.sql.exec('SELECT id,state,fingerprint FROM jobs WHERE request_key=?',requestKey).toArray()[0];",`if(!isMutation(task.op)&&this.sql.exec('SELECT id FROM pending_consent_v2 WHERE id=?',requestKey).toArray().length)return finish({error:'pending_key_reserved'},409);
     const previous=this.sql.exec('SELECT id,state,fingerprint FROM jobs WHERE request_key=?',requestKey).toArray()[0];`);
if(target==='ha')outer=inner;
outer=one(outer,"return internal(env,'/enqueue','POST',{task,request_key});","return internal(env,'/enqueue','POST',{task,request_key,client_proof:request.headers.get('X-Operation-Proof')});");
outer=one(outer,"if(path==='/v1/owner/approve-operation'&&method==='POST')return internal(env,'/approve-operation','POST',await body(request));",`if(path==='/v1/owner/approve-operation'&&method==='POST')return internal(env,'/approve-operation','POST',await body(request));
   if(path==='/v1/owner/revoke-operation'&&method==='POST')return internal(env,'/revoke-operation','POST',await body(request,2000));`);
outer=one(outer,"if(path==='/v1/jobs'&&method==='POST')return enqueue(request,env,await body(request));",`if(path==='/v1/operation-pending'&&method==='POST')return internal(env,'/operation-pending','POST',await body(request));
   if(path==='/v1/jobs'&&method==='POST')return enqueue(request,env,await body(request));`);
// The approval capability is now server-held. Legacy named args cannot carry it.
outer=one(outer,',confirmed:args.confirmed,approval_id:args.approval_id});\n    else if(name===\'read_file\')',",confirmed:args.confirmed});\n    else if(name==='read_file')");
outer=one(outer,',confirmed:args.confirmed,approval_id:args.approval_id});\n    else if(name===\'queue_diagnostic\')',",confirmed:args.confirmed});\n    else if(name==='queue_diagnostic')");
if(target==='ha')outer=one(outer,"tools.push({...spec, name: alias, description: specs.get(alias),",`tools.push({...spec, name: alias, description: specs.get(alias)+(['ha_write_file','ha_exec_command'].includes(alias)?' Requires an independently approved, signed pending request supplied by the trusted transport. ChatGPT confirmation remains separate.':''),`);
// Metadata only, never a claim of host confirmation. Keep all existing annotations.
const roots=new Set([dirname(entry),dirname(coord)]);
const sidecars=[];
for(const root of roots){const p=join(root,'operation-consent.mjs');let s=readFileSync(p,'utf8');s=one(s,"    approval_id: { type: 'string', format: 'uuid', description: 'One-time exact-operation approval from the authenticated owner channel. Required for writes and command execution.' },\n",'');s=one(s,"return { ...tool, annotations, inputSchema };","return { ...tool, description: tool.description + ' Requires an independently approved, signed pending request supplied by the trusted transport. ChatGPT confirmation remains separate.', annotations, inputSchema };");sidecars.push([p,s]);}
// All edits above must validate before writing any file.
writeFileSync(entry,imported+outer);if(target!=='ha')writeFileSync(coord,imported+inner);
for(const [p,s] of sidecars)writeFileSync(p,s);
for(const root of roots)copyFileSync(new URL('pending-consent.mjs',import.meta.url),join(root,'pending-consent.mjs'));
