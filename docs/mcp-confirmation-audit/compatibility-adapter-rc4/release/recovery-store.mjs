// Node-local reference recovery store. No task, credentials, private key or proof
// is persisted. The directory must be preprovisioned privately by the owner.
// A production distributed adapter must use an equivalent durable store and
// independently attest its single writer/recovery semantics before release.
import {DatabaseSync} from 'node:sqlite';
import {lstatSync,openSync,closeSync,constants} from 'node:fs';
import {isAbsolute,dirname} from 'node:path';
const uuid=/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/;
const hex=/^[a-f0-9]{64}$/;
const scopes=['keenetic','ha'];
const outcomes=['unknown_submission','queued','denied'];
const owner=()=>process.getuid?.();
const privateMode=s=>s.uid===owner()&&(s.mode&0o077)===0;
function securePath(path){
 if(typeof path!=='string'||!isAbsolute(path)||owner()===undefined)throw Error('private_store_required');
 const d=lstatSync(dirname(path));if(!d.isDirectory()||d.isSymbolicLink()||!privateMode(d))throw Error('private_store_required');
 // The parent is owner-only, and the final filename is not a symlink.
 let fd;try{fd=openSync(path,constants.O_WRONLY|constants.O_CREAT|constants.O_EXCL|constants.O_NOFOLLOW,0o600);}catch(e){if(e.code!=='EEXIST')throw e;}finally{if(fd!==undefined)closeSync(fd);}
 const f=lstatSync(path);if(!f.isFile()||f.nlink!==1||!privateMode(f))throw Error('private_store_required');
}
export function openRecoveryStore(path,{maxRecords=1000}={}){
 if(!Number.isInteger(maxRecords)||maxRecords<1||maxRecords>10000)throw Error('invalid_store_capacity');securePath(path);
 const db=new DatabaseSync(path);db.exec('PRAGMA journal_mode=DELETE; PRAGMA synchronous=FULL; PRAGMA busy_timeout=5000;');
 db.exec(`CREATE TABLE IF NOT EXISTS dispatch (ref TEXT PRIMARY KEY, target TEXT NOT NULL, request_key TEXT NOT NULL UNIQUE, client_hash TEXT NOT NULL, owner_hash TEXT NOT NULL, created INTEGER NOT NULL, outcome TEXT NOT NULL CHECK(outcome IN ('unknown_submission','queued','denied')))`);
 const get=db.prepare('SELECT * FROM dispatch WHERE ref=? AND target=?'), count=db.prepare('SELECT COUNT(*) AS n FROM dispatch'), insert=db.prepare("INSERT INTO dispatch VALUES(?,?,?,?,?,?,'unknown_submission')"), set=db.prepare('UPDATE dispatch SET outcome=? WHERE ref=? AND target=? AND outcome=\'unknown_submission\'');
 return Object.freeze({
  begin(r){if(!uuid.test(r?.ref??'')||!uuid.test(r?.requestKey??'')||!scopes.includes(r?.target)||!hex.test(r?.clientHash??'')||!hex.test(r?.ownerHash??'')||!Number.isSafeInteger(r?.created)||r.created<0)throw Error('invalid_dispatch_record');db.exec('BEGIN IMMEDIATE');try{if(count.get().n>=maxRecords)throw Error('recovery_capacity');insert.run(r.ref,r.target,r.requestKey,r.clientHash,r.ownerHash,r.created);db.exec('COMMIT');}catch(e){db.exec('ROLLBACK');throw e;}},
  get(ref,target){if(!uuid.test(ref??'')||!scopes.includes(target))return null;const r=get.get(ref,target);return r?{ref:r.ref,target:r.target,requestKey:r.request_key,clientHash:r.client_hash,ownerHash:r.owner_hash,created:r.created,outcome:r.outcome}:null;},
  outcome(ref,target,outcome){if(!uuid.test(ref??'')||!scopes.includes(target)||!outcomes.includes(outcome))throw Error('invalid_dispatch_outcome');return set.run(outcome,ref,target).changes===1;},
  close(){db.close();}
 });
}
