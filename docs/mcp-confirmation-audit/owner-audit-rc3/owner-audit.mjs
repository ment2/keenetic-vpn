// Additive consent audit, using the existing bounded redacted audit table.
// All writes must occur inside the coordinator transaction. Never expose id in audit.
import { auditOutcome } from './operation-consent.mjs';
const TTL=120000;
const transitions=new Set(['registered','approved','revoked','consumed']);
export function createOwnerAudit(sql){
 sql.exec('CREATE TABLE IF NOT EXISTS pending_owner_audit_v3 (id TEXT PRIMARY KEY, correlation TEXT NOT NULL, expires INTEGER NOT NULL)');
 sql.exec('CREATE INDEX IF NOT EXISTS pending_owner_audit_v3_expiry ON pending_owner_audit_v3(expires)');
}
export function ownerTransition(sql,id,outcome,now){
 if(!transitions.has(outcome))throw Error('invalid_owner_audit_transition');
 // The caller has already checked the pending row and made the successful transition.
 const row=sql.exec('SELECT expires FROM pending_consent_v2 WHERE id=?',id).toArray()[0];
 if(!row||row.expires<=now||row.expires>now+TTL)throw Error('invalid_pending_audit_row');
 sql.exec('DELETE FROM pending_owner_audit_v3 WHERE expires<=?',now);
 let link=sql.exec('SELECT correlation,expires FROM pending_owner_audit_v3 WHERE id=?',id).toArray()[0];
 if(!link){
  // Old RC2 rows may lack links; production cutover must invalidate them by revision.
  const correlation=crypto.randomUUID();
  sql.exec('INSERT INTO pending_owner_audit_v3 VALUES(?,?,?)',id,correlation,row.expires);
  link={correlation,expires:row.expires};
 }
 if(link.expires!==row.expires)throw Error('pending_audit_expiry_mismatch');
 auditOutcome(sql,link.correlation,'owner_consent',outcome,now);
 return link.correlation;
}
export function ownerDenied(sql,action,now){
 if(!['approve_denied','revoke_denied'].includes(action))throw Error('invalid_owner_audit_action');
 // Mismatched/unknown requests must not be associated with an existing client's correlation.
 auditOutcome(sql,crypto.randomUUID(),'owner_consent',action,now);
}
