import { cpSync, readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, join } from 'node:path';

const [target, entry, coordinator, expectedEntry, expectedCoordinator] = process.argv.slice(2);
if (!['keenetic', 'ha'].includes(target) || !entry || !coordinator) {
  throw Error('Usage: node apply-operation-consent.mjs keenetic|ha ENTRY COORDINATOR ENTRY_SHA256 COORDINATOR_SHA256');
}
const bundled = target === 'ha';
if (bundled !== (entry === coordinator)) throw Error('HA uses a bundle and Keenetic uses separate modules');
function checked(path, expected) {
  const bytes = readFileSync(path);
  if (!/^[a-f0-9]{64}$/.test(expected ?? '') || createHash('sha256').update(bytes).digest('hex') !== expected) {
    throw Error('Baseline checksum mismatch');
  }
  return bytes.toString('utf8').replaceAll('\r\n', '\n');
}
let outer = checked(entry, expectedEntry);
let inner = checked(coordinator, expectedCoordinator);
function replace(source, needle, replacement) {
  const i = source.indexOf(needle);
  if (i < 0 || source.indexOf(needle, i + needle.length) >= 0) throw Error('Unexpected source layout: ' + needle);
  return source.slice(0, i) + replacement + source.slice(i + needle.length);
}

const enqueue = "if(path==='/enqueue'&&request.method==='POST'){";
inner = replace(inner, enqueue, `if(path==='/operation-audit'&&request.method==='GET'){
    return response({events:this.sql.exec('SELECT correlation,stage,outcome,at FROM operation_audit WHERE at>=? ORDER BY seq DESC LIMIT 100',now-604800000).toArray()});
   }
   if(path==='/approve-operation'&&request.method==='POST'){
    let candidate;
    try {
     candidate=await body(request);
     if(candidate.confirmed!==true)throw Error('explicit_owner_confirmation_required');
     if(Object.keys(candidate).some(k=>!['op','command','timeout','path','content','mode','confirmed'].includes(k)))throw Error('invalid_task');
    }catch{return response({error:'invalid_owner_confirmation'},400);}
    let task;
    try{task=taskFromBody(candidate);}catch{return response({error:'invalid_task'},400);}
    if(!isMutation(task.op))return response({error:'invalid_task'},400);
    if(task.op==='write_file')task.content_sha256=await contentHash(task.content);
    const fingerprint=await digest(task);
    return this.tx(()=>{
     const policy=this.policy(), denied=mutationDenial(policy,task,candidate);
     if(denied)return response({error:denied},403);
     this.sql.exec('DELETE FROM exact_consent WHERE expires<=? OR revision<>?',now,policy.revision);
     if(this.sql.exec('SELECT COUNT(*) AS n FROM exact_consent').toArray()[0].n>=100)return response({error:'approval_capacity'},503);
     const approval_id=crypto.randomUUID();
     this.sql.exec('INSERT INTO exact_consent VALUES(?,?,?,?)',approval_id,fingerprint,policy.revision,now+120000);
     return response({approval_id,expires_in:120},201);
    });
   }
   ${enqueue}
    const correlation=crypto.randomUUID();
    auditOutcome(this.sql,correlation,'received','enqueue',now);
    let decisionStored=false;
    const finish=(value,status)=>{
     if(!decisionStored)auditOutcome(this.sql,correlation,'decision',value.error?'denied':'allowed',now);
     auditOutcome(this.sql,correlation,'result',value.error??(value.already_received?'deduplicated':'queued'),now);
     const reply=response(value,status);
     reply.headers.set('x-operation-correlation',correlation);
     return reply;
    };
    try{`);
const table = 'this.sql.exec(`CREATE TABLE IF NOT EXISTS audit ';
inner = replace(inner, table, 'createConsentTables(this.sql);\n  '+table);
inner = replace(inner, "event(event,id,p,now){", "event(event,id,p,now){auditLifecycle(this.sql,event,id,now);");
const start = inner.indexOf('const correlation=crypto.randomUUID();', inner.indexOf(enqueue));
const end = inner.indexOf("if(path==='/claim'", start);
if (start < 0 || end < 0) throw Error('Missing queue boundary');
let section = inner.slice(start, end);
section = replace(section, 'const b=await body(request);let task;', "let b;try{b=await body(request);}catch{return finish({error:'invalid_task'},400);}let task;");
section = section.replaceAll('return response(', 'return finish(');
const policyStart = section.indexOf('const p=this.policy();if(!p.enabled)');
const policyEnd = section.indexOf('const previous=', policyStart);
if (policyStart < 0 || policyEnd < 0 || !section.slice(policyStart,policyEnd).includes("b.task.confirmed!==true")) throw Error('Unexpected authorization predicate');
section = section.slice(0,policyStart) + `const p=this.policy(), denied=mutationDenial(p,task,b.task);
     if(denied)return finish({error:denied},denied==='invalid_confirmation_argument'?400:403);
     ` + section.slice(policyEnd);
const insert = "this.sql.exec('INSERT INTO jobs(";
section = replace(section, insert, `if(isMutation(task.op)&&!consumeApproval(this.sql,b.task.approval_id,fingerprint,p.revision,Date.now()))
      return finish({error:'exact_operation_approval_required'},403);
     ${insert}`);
section = replace(section, "\n    });\n   }", "\n    });\n    }catch{return finish({error:'bridge_failure'},503);}\n   }");
section = replace(section, "this.event('queued',id,p,now);", "linkOperation(this.sql,id,correlation,now);this.event('queued',id,p,now);");
inner = inner.slice(0,start) + section.replace('    let decisionStored=false;\n','').replace('if(!decisionStored)auditOutcome','auditOutcome') + inner.slice(end);
if (bundled) outer = inner;
const owner = "if(path==='/v1/owner/permissions'&&method==='POST')";
outer = replace(outer, owner, `if(path==='/v1/owner/approve-operation'&&method==='POST')return internal(env,'/approve-operation','POST',await body(request));
   if(path==='/v1/owner/operation-audit'&&method==='GET')return internal(env,'/operation-audit');
   ${owner}`);
outer = replace(outer, "destructiveHint:false}}))]", "destructiveHint:false}}))].map(describeTool)");
outer = replace(outer, 'const payload=await r.json();return ok(', 'const payload=await r.json();const reply=ok(');
outer = replace(outer, 'structuredContent:payload,isError:!r.ok});', `structuredContent:payload,isError:!r.ok});
    const correlation=r.headers.get('x-operation-correlation');
    if(correlation)reply.headers.set('x-operation-correlation',correlation);
    return reply;`);
for (const ending of ['timeout:args.timeout,confirmed:args.confirmed', 'content:args.content,confirmed:args.confirmed']) {
  outer = replace(outer, ending, ending + ',approval_id:args.approval_id');
}
if (bundled && outer.includes("name:'ha_get_oauth_audit'")) {
  outer = replace(outer, 'idempotentHint:true,destructiveHint:false},securitySchemes', 'idempotentHint:true,destructiveHint:false,openWorldHint:false},securitySchemes');
}
const importLine = "import { auditLifecycle, auditOutcome, consumeApproval, createConsentTables, describeTool, isMutation, linkOperation, mutationDenial } from './operation-consent.mjs';\n";
writeFileSync(entry, importLine + outer);
if (!bundled) writeFileSync(coordinator, importLine + inner);
for (const path of new Set([dirname(entry), dirname(coordinator)])) {
  for (const file of ['confirmation-contract.mjs', 'operation-consent.mjs']) {
    cpSync(new URL(file, import.meta.url), join(path,file));
  }
}
