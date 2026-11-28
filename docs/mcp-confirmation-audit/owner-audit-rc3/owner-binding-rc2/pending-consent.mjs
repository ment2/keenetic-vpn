// RC2 source candidate. No device I/O; no host approval emulation.
const uuid=/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/;
const hex64=/^[a-f0-9]{64}$/;
const pubhex=/^04[a-f0-9]{128}$/;
const sighex=/^[a-f0-9]{128}$/;
const encoder=new TextEncoder();
const bytes=h=>Uint8Array.from(h.match(/../g),v=>parseInt(v,16));
export const hex=b=>Array.from(new Uint8Array(b),v=>v.toString(16).padStart(2,'0')).join('');
export const sha=async data=>hex(await crypto.subtle.digest('SHA-256',data));
export const fingerprint=async task=>sha(encoder.encode(JSON.stringify(task)));
export const message=(target,phase,id,digest,challenge='')=>encoder.encode(JSON.stringify(['operation-consent-rc2',target,phase,id,digest,challenge]));
export const validId=id=>typeof id==='string'&&uuid.test(id);
const exact=(b,keys)=>b&&typeof b==='object'&&!Array.isArray(b)&&Object.keys(b).length===keys.length&&keys.every(k=>Object.hasOwn(b,k));
const validTarget=t=>t==='keenetic'||t==='ha';
const validDigest=d=>typeof d==='string'&&hex64.test(d);
export const pendingShape=b=>exact(b,['request_key','task','public_key','registration_proof'])&&validId(b.request_key)&&typeof b.public_key==='string'&&pubhex.test(b.public_key)&&typeof b.registration_proof==='string'&&sighex.test(b.registration_proof);
export const approveShape=b=>exact(b,['request_key','task','client_key_sha256','challenge','confirmed'])&&validId(b.request_key)&&validDigest(b.client_key_sha256)&&validId(b.challenge)&&b.confirmed===true;
export const revokeShape=b=>exact(b,['request_key','client_key_sha256','challenge'])&&validId(b.request_key)&&validDigest(b.client_key_sha256)&&validId(b.challenge);
export async function verifyProof(target,phase,id,digest,publicKey,proof,challenge=''){
 if(!validTarget(target)||!['register','consume'].includes(phase)||!validId(id)||!validDigest(digest)||(phase==='consume'?!validId(challenge):challenge!=='')||typeof publicKey!=='string'||!pubhex.test(publicKey)||typeof proof!=='string'||!sighex.test(proof))return false;
 try{const key=await crypto.subtle.importKey('raw',bytes(publicKey),{name:'ECDSA',namedCurve:'P-256'},false,['verify']);return await crypto.subtle.verify({name:'ECDSA',hash:'SHA-256'},key,bytes(proof),message(target,phase,id,digest,challenge));}catch{return false;}
}
export function createPendingTable(sql){
 sql.exec(`CREATE TABLE IF NOT EXISTS pending_consent_v2 (id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, key_hex TEXT NOT NULL, key_hash TEXT NOT NULL, challenge TEXT NOT NULL, revision INTEGER NOT NULL, expires INTEGER NOT NULL, state TEXT NOT NULL CHECK(state IN ('pending','approved','revoked','consumed'))) `);
 sql.exec('CREATE INDEX IF NOT EXISTS pending_consent_v2_expiry ON pending_consent_v2(expires)');
}
const row=(sql,id)=>sql.exec('SELECT * FROM pending_consent_v2 WHERE id=?',id).toArray()[0];
// All mutating functions below must be called within the coordinator's synchronous storage transaction.
// Registration is first authenticated by the existing bridge bearer/OAuth boundary, then proves key possession.
export function registerPending(sql,{id,digest,publicKey,keyHash,revision,now}){
 sql.exec('DELETE FROM pending_consent_v2 WHERE expires<=?',now);
 if(row(sql,id))return 'pending_conflict';
 if(sql.exec('SELECT COUNT(*) AS n FROM pending_consent_v2').toArray()[0].n>=100)return 'pending_capacity';
 // A request key already used by a job may not be re-registered after expiry.
 if(sql.exec('SELECT id FROM jobs WHERE request_key=?',id).toArray().length)return 'pending_conflict';
 const challenge=crypto.randomUUID();
 sql.exec("INSERT INTO pending_consent_v2 VALUES(?,?,?,?,?,?,?,'pending')",id,digest,publicKey,keyHash,challenge,revision,now+120000);
 return {challenge};
}
export function approvePending(sql,{id,digest,keyHash,challenge,revision,now}){
 return sql.exec("UPDATE pending_consent_v2 SET state='approved' WHERE id=? AND fingerprint=? AND key_hash=? AND challenge=? AND revision=? AND expires>? AND state='pending' RETURNING id",id,digest,keyHash,challenge,revision,now).toArray().length===1;
}
export function revokePending(sql,{id,keyHash,challenge,now}){
 return sql.exec("UPDATE pending_consent_v2 SET state='revoked' WHERE id=? AND key_hash=? AND challenge=? AND expires>? AND state IN ('pending','approved') RETURNING id",id,keyHash,challenge,now).toArray().length===1;
}
// Async signature verification BEFORE the transaction; immutable identity fields are rechecked atomically.
export async function checkPendingProof(sql,{target,id,digest,proof}){
 if(!validId(id))return null;
 const p=row(sql,id);
 if(!p||p.fingerprint!==digest||p.expires<=Date.now()||!['approved','consumed'].includes(p.state))return null;
 if(!await verifyProof(target,'consume',id,digest,p.key_hex,proof,p.challenge))return null;
 return Object.freeze({id,digest,keyHash:p.key_hash,publicKey:p.key_hex,challenge:p.challenge});
}
export function pendingAuthorized(sql,checked,revision,now,allowConsumed=false){
 if(!checked)return false;
 const p=row(sql,checked.id);
 return !!p&&p.fingerprint===checked.digest&&p.key_hash===checked.keyHash&&p.key_hex===checked.publicKey&&p.challenge===checked.challenge&&p.revision===revision&&p.expires>now&&(p.state==='approved'||(allowConsumed&&p.state==='consumed'));
}
export function consumePending(sql,checked,revision,now){
 if(!pendingAuthorized(sql,checked,revision,now))return false;
 return sql.exec("UPDATE pending_consent_v2 SET state='consumed' WHERE id=? AND fingerprint=? AND key_hash=? AND key_hex=? AND challenge=? AND revision=? AND expires>? AND state='approved' RETURNING id",checked.id,checked.digest,checked.keyHash,checked.publicKey,checked.challenge,revision,now).toArray().length===1;
}
export function clientKeyHash(key){if(typeof key!=='string'||!pubhex.test(key))throw Error('invalid_public_key');return sha(bytes(key));}
// Transport creates a fresh nonextractable private key per pending call; not a model tool.
// The owner must independently verify the public key fingerprint against the intended trusted transport.
export async function createClientProof(target,normalizedTask){
 if(!validTarget(target))throw Error('invalid_target');
 const snapshot=Object.freeze(JSON.parse(JSON.stringify(normalizedTask)));
 const task={...snapshot};
 if(task.op==='write_file')task.content_sha256=await sha(encoder.encode(task.content));
 const digest=await fingerprint(task),id=crypto.randomUUID();
 const key=await crypto.subtle.generateKey({name:'ECDSA',namedCurve:'P-256'},false,['sign','verify']);
 const publicKey=hex(await crypto.subtle.exportKey('raw',key.publicKey));
 const keyHash=await clientKeyHash(publicKey);
 const sign=async (phase,challenge='')=>hex(await crypto.subtle.sign({name:'ECDSA',hash:'SHA-256'},key.privateKey,message(target,phase,id,digest,challenge)));
 const registration={request_key:id,task:snapshot,public_key:publicKey,registration_proof:await sign('register')};
 let sent=false;
 return Object.freeze({registration:Object.freeze(registration),ownerReview(challenge){if(!validId(challenge))throw Error('invalid_challenge');return Object.freeze({request_key:id,client_key_sha256:keyHash,challenge,task:snapshot});},async headersOnce(challenge){if(sent)throw Error('already_sent');if(!validId(challenge))throw Error('invalid_challenge');sent=true;return {'Idempotency-Key':id,'X-Operation-Proof':await sign('consume',challenge)};}});
}
