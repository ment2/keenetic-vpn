// Run only on disposable RC2 source copies. Verify all inputs before writing.
import {readFileSync,writeFileSync,copyFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {dirname,join} from 'node:path';
const [target,entry,coord,entryHash,coordHash]=process.argv.slice(2);
if(!['keenetic','ha'].includes(target)||!entry||!coord||(target==='ha')!==(entry===coord))throw Error('invalid_target');
function checked(p,h){const b=readFileSync(p);if(!/^[a-f0-9]{64}$/.test(h??'')||createHash('sha256').update(b).digest('hex')!==h)throw Error('baseline hash mismatch');return b.toString('utf8');}
function one(s,a,b){if(s.split(a).length!==2)throw Error('unexpected anchor: '+a.slice(0,100));return s.replace(a,b);}
const outer=checked(entry,entryHash);let s=checked(coord,coordHash);
s=one(s,'createConsentTables(this.sql);createPendingTable(this.sql);','createConsentTables(this.sql);createPendingTable(this.sql);createOwnerAudit(this.sql);');
s=one(s,"if(revoking)return this.tx(()=>revokePending(this.sql,{id:b.request_key,keyHash:b.client_key_sha256,challenge:b.challenge,now:Date.now()})?response({status:'revoked'}):response({error:'pending_not_revocable'},409));",`if(revoking)return this.tx(()=>{const current=Date.now();
     if(!revokePending(this.sql,{id:b.request_key,keyHash:b.client_key_sha256,challenge:b.challenge,now:current})){ownerDenied(this.sql,'revoke_denied',current);return response({error:'pending_not_revocable'},409);}
     ownerTransition(this.sql,b.request_key,'revoked',current);return response({status:'revoked'});});`);
s=one(s,"return response({request_key:b.request_key,client_key_sha256:keyHash,challenge:registered.challenge,expires_in:120},201);",`ownerTransition(this.sql,b.request_key,'registered',current);
      return response({request_key:b.request_key,client_key_sha256:keyHash,challenge:registered.challenge,expires_in:120},201);`);
s=one(s,"return approvePending(this.sql,{id:b.request_key,digest:fp,keyHash,challenge:b.challenge,revision:p.revision,now:current})?response({status:'approved'}):response({error:'pending_not_approvable'},409);",`if(!approvePending(this.sql,{id:b.request_key,digest:fp,keyHash,challenge:b.challenge,revision:p.revision,now:current})){ownerDenied(this.sql,'approve_denied',current);return response({error:'pending_not_approvable'},409);}
     ownerTransition(this.sql,b.request_key,'approved',current);return response({status:'approved'});`);
s=one(s,"if(isMutation(task.op)&&!consumePending(this.sql,checked,p.revision,Date.now()))\n      return finish({error:'pending_client_proof_required'},403);",`if(isMutation(task.op)){const current=Date.now();if(!consumePending(this.sql,checked,p.revision,current))return finish({error:'pending_client_proof_required'},403);
      ownerTransition(this.sql,requestKey,'consumed',current);}`);
// Keep the owner transition and queue insert in the same transaction. The per-request
// audit retains its separate correlation; no public link to job ID is introduced.
const imp="import {createOwnerAudit,ownerTransition,ownerDenied} from './owner-audit.mjs';\n";
writeFileSync(coord,imp+s);copyFileSync(new URL('owner-audit.mjs',import.meta.url),join(dirname(coord),'owner-audit.mjs'));
