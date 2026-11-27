import {DatabaseSync} from 'node:sqlite';
import assert from 'node:assert/strict';
import test from 'node:test';
import {pathToFileURL} from 'node:url';
import {resolve} from 'node:path';
import {createClientProof,hex,sha,verifyProof,fingerprint,message} from './pending-consent.mjs';
const [keenetic,ha,keeneticBase,haBase]=process.argv.slice(2);
const admin='synthetic-admin'.padEnd(40,'a'),agent='synthetic-agent'.padEnd(40,'b'),policy='synthetic-policy'.padEnd(40,'c');
globalThis.fetch=()=>{throw Error('NETWORK_FORBIDDEN');};
const task=Object.freeze({op:'write_file',path:'/synthetic-unit/only.txt',content:'synthetic-fixture',timeout:20});
const noTask=Object.freeze({op:'exec',command:'echo SYNTHETIC-NOT-EXECUTED',timeout:20});
const auth={authorization:'Bearer '+admin};
const owner={...auth,'x-control-policy-token':policy};
const agentAuth={authorization:'Bearer '+agent};
const ordinary={path:task.path,content:task.content,confirmed:true};
for(const [target,file,baseline] of [['keenetic',keenetic,keeneticBase],['ha',ha,haBase]]){
 test(target+' source + Node SQLite shim',async t=>{
  const db=new DatabaseSync(':memory:');t.after(()=>db.close());
  const sql={exec(q,...args){const stmt=db.prepare(q);const rows=stmt.columns().length?stmt.all(...args):(stmt.run(...args),[]);return {toArray:()=>rows,[Symbol.iterator]:()=>rows[Symbol.iterator]()};}};
  const storage={sql,transactionSync(fn){db.exec('BEGIN IMMEDIATE');try{const r=fn();db.exec('COMMIT');return r;}catch(e){db.exec('ROLLBACK');throw e;}}};
  let worker,env;
  async function load(p){const m=await import(pathToFileURL(resolve(p)));worker=m.default;env={CONTROL_ADMIN_TOKEN:admin,CONTROL_AGENT_TOKEN:agent,CONTROL_POLICY_TOKEN:policy,CONTROL_DATA_KEY:'ab'.repeat(32),...(target==='ha'?{TARGET_DEVICE:'homeassistant'}:{})};const coord=new m.QueueCoordinator({storage},env);env.CONTROL_QUEUE={idFromName:n=>n,get:n=>({fetch:r=>coord.fetch(r)})};}
  await load(file);
  async function req(path,body,headers=auth){const r=await worker.fetch(new Request('https://synthetic.invalid'+path,{method:body===undefined?'GET':'POST',headers:{...headers,'content-type':'application/json'},...(body===undefined?{}:{body:JSON.stringify(body)})}),env,{});return {status:r.status,headers:r.headers,value:r.status===204?null:await r.json()};}
  const prefix=target==='ha'?'ha_':'';
  const rpc=(method,params,headers=auth)=>req('/mcp',{jsonrpc:'2.0',id:1,method,params},headers);
  const write=(a=ordinary,headers=auth)=>rpc('tools/call',{name:prefix+'write_file',arguments:a},headers);
  const outcome=r=>r.value?.result?.structuredContent??r.value;
  const setPolicy=async (owner_admin_enabled=true,scopes=['write_file','exec','diagnostic','read_file'])=>assert.equal((await req('/v1/owner/permissions',{remote_enabled:true,owner_admin_enabled,scopes},owner)).status,200);
  const register=async(task=undefined)=>{const c=await createClientProof(target,task??ordinaryTask());const r=await req('/v1/operation-pending',c.registration);assert.equal(r.status,201,JSON.stringify(r.value));assert.equal(r.value.request_key,c.registration.request_key);const review=c.ownerReview(r.value.challenge);assert.equal(r.value.client_key_sha256,review.client_key_sha256);return {c,review};};
  function ordinaryTask(){return task;}
  const approve=(p,headers=owner)=>req('/v1/owner/approve-operation',{...p.review,confirmed:true},headers);
  const revoke=p=>{const {request_key,client_key_sha256,challenge}=p.review;return req('/v1/owner/revoke-operation',{request_key,client_key_sha256,challenge},owner);};
  const proof=async p=>({...auth,...await p.c.headersOnce(p.review.challenge)});
  const count=()=>db.prepare('SELECT COUNT(*) AS n FROM jobs').get().n;
  await setPolicy();
  await t.test('catalog and unauthenticated boundaries',async()=>{
   const tools=(await rpc('tools/list')).value.result.tools,spec=tools.find(x=>x.name===prefix+'write_file');assert.equal(spec.annotations.destructiveHint,true);assert.equal(spec.annotations.readOnlyHint,false);assert.equal(spec.annotations.idempotentHint,false);assert.equal(spec.inputSchema.properties.approval_id,undefined);assert.match(spec.description,/signed pending request/);if(target==='ha')assert.deepEqual(spec.securitySchemes,[{type:'oauth2',scopes:['ha:control']}]);
   const c=await createClientProof(target,task);assert.equal((await req('/v1/operation-pending',c.registration,{})).status,401);assert.equal((await req('/v1/operation-pending',{...c.registration,registration_proof:'00'.repeat(64)})).status,403);
   const other=await createClientProof(target==='ha'?'keenetic':'ha',task);assert.equal((await req('/v1/operation-pending',other.registration)).status,403);assert.equal(count(),0);
  });
  await t.test('owner approval exact and non-automatic',async()=>{
   const p=await register();assert.equal((await approve(p,auth)).status,401);assert.equal((await req('/v1/owner/approve-operation',{...p.review,confirmed:'true'},owner)).status,400);
   assert.equal((await req('/v1/owner/approve-operation',{...p.review,confirmed:true,task:{...task,content:'changed'}},owner)).status,409);
   assert.equal((await req('/v1/owner/approve-operation',{...p.review,confirmed:true,client_key_sha256:'ab'.repeat(32)},owner)).status,409);
   assert.equal((await req('/v1/owner/approve-operation',{...p.review,confirmed:true,challenge:crypto.randomUUID()},owner)).status,409);
   assert.equal((await approve(p)).status,200);assert.equal((await approve(p)).status,409);assert.equal((await revoke(p)).status,200);assert.equal(count(),0);
  });
  await t.test('old grants and wrong key cannot enqueue',async()=>{
   const p=await register(),q=await register();assert.equal((await approve(p)).status,200);assert.equal((await approve(q)).status,200);
   assert.equal(outcome(await write()).error,'pending_client_proof_required');assert.equal(outcome(await write({...ordinary,approval_id:crypto.randomUUID()})).error,'pending_client_proof_required');
   const wrong=await proof(q);wrong['Idempotency-Key']=p.review.request_key;
   assert.equal(outcome(await write(ordinary,wrong)).error,'pending_client_proof_required');
   const h=await proof(p);assert.equal(outcome(await write({...ordinary,content:'changed'},h)).error,'pending_client_proof_required');
   assert.equal(outcome(await write({...ordinary,confirmed:'true'},h)).error,'invalid_confirmation_argument');assert.equal(outcome(await write({...ordinary,confirmed:false},h)).error,'confirmation_required');
   assert.equal((await revoke(p)).status,200);assert.equal(outcome(await write(ordinary,h)).error,'pending_client_proof_required');assert.equal((await revoke(q)).status,200);assert.equal(count(),0);
  });
  await t.test('revocation and policy revision/expiry',async()=>{
   const p=await register();assert.equal((await approve(p)).status,200);const h=await proof(p);assert.equal((await revoke(p)).status,200);assert.equal(outcome(await write(ordinary,h)).error,'pending_client_proof_required');
   const q=await register();assert.equal((await approve(q)).status,200);const h2=await proof(q);await setPolicy(false);assert.equal(outcome(await write(ordinary,h2)).error,'pending_client_proof_required');await setPolicy();
   const r=await register();assert.equal((await approve(r)).status,200);const h3=await proof(r);db.prepare('UPDATE pending_consent_v2 SET expires=? WHERE id=?').run(Date.now()-1,r.review.request_key);assert.equal(outcome(await write(ordinary,h3)).error,'pending_client_proof_required');
   const oldChallenge=r.review.challenge;const replay=await req('/v1/operation-pending',r.c.registration);assert.equal(replay.status,201);assert.notEqual(replay.value.challenge,oldChallenge);assert.equal((await approve(r)).status,409);assert.equal(outcome(await write(ordinary,h3)).error,'pending_client_proof_required');assert.equal(count(),0);
  });
  let completed;
  await t.test('parallel same-request calls insert exactly one; only same proof gets dedup result',async()=>{
   const p=await register();assert.equal((await approve(p)).status,200);const h=await proof(p);await assert.rejects(p.c.headersOnce(p.review.challenge),/already_sent/);
   const results=await Promise.all([write(ordinary,h),write(ordinary,h)]);const values=results.map(outcome);assert.ok(values.every(x=>x.status==='queued'));assert.equal(values.filter(x=>x.already_received).length,1);assert.equal(values[0].id,values[1].id);assert.equal(count(),1);
   assert.equal(outcome(await write(ordinary,{...auth,'Idempotency-Key':p.review.request_key})).error,'pending_client_proof_required');assert.equal((await revoke(p)).status,409);
   const claim=await req('/v1/agent/next',undefined,agentAuth);assert.equal(claim.status,200);assert.equal(claim.value.content,task.content);assert.equal(claim.value.id,values[0].id);completed=claim.value.id;
   assert.equal((await req('/v1/agent/result/'+completed,{lease_id:claim.value.lease_id,exit_code:0,output:'synthetic-result'},agentAuth)).status,200);
  });
  await t.test('REST, exec alias, legacy mapping and nonmutating reserved key',async()=>{
   const p=await register(noTask);assert.equal((await approve(p)).status,200);const h=await proof(p);
   const reserved=await req('/v1/jobs',{op:'diagnostic',command:'status'},h);assert.equal(reserved.status,409);assert.equal(reserved.value.error,'pending_key_reserved');
   const resp=await rpc('tools/call',{name:prefix+'exec_command',arguments:{command:noTask.command,timeout:20,confirmed:true}},h);assert.equal(outcome(resp).status,'queued');
   const q=await register();assert.equal((await approve(q)).status,200);const h2=await proof(q);const rest=await req('/v1/jobs',{...task,confirmed:true},h2);assert.equal(rest.status,202);
   if(target==='keenetic'){const l=await register();assert.equal((await approve(l)).status,200);const h3=await proof(l);const legacy=await rpc('tools/call',{name:'queue_router_task',arguments:{...task,confirmed:true}},h3);assert.equal(outcome(legacy).status,'queued');}
  });
  await t.test('race revoke versus enqueue, at most one wins',async()=>{
   const p=await register();assert.equal((await approve(p)).status,200);const h=await proof(p),before=count();const [a,b]=await Promise.all([revoke(p),write(ordinary,h)]);const queued=outcome(b).status==='queued';assert.equal(Number(a.status===200)+Number(queued),1);assert.equal(count(),before+Number(queued));
  });
  await t.test('bounded redacted audit and rollback preserves finished job',async()=>{
   const a=await req('/v1/owner/operation-audit',undefined,owner);assert.equal(a.status,200);assert.ok(a.value.events.length<=100);const serialized=JSON.stringify(a.value.events);for(const v of [task.path,task.content,admin,policy,agent,completed])assert.ok(!serialized.includes(v));
   await setPolicy(); // invalidates pending; cancels any queued synthetic tasks by existing policy semantics.
   const preserved=(await req('/v1/jobs/'+completed)).value;assert.equal(preserved.status,'done');assert.equal(preserved.output,'synthetic-result');
   await load(baseline);assert.equal((await req('/v1/owner/operation-audit',undefined,owner)).status,404);assert.equal((await req('/v1/jobs/'+completed)).value.status,'done');
   await load(file);assert.equal((await req('/v1/jobs/'+completed)).value.status,'done');assert.equal((await req('/v1/owner/operation-audit',undefined,owner)).status,200);
  });
 });
}
