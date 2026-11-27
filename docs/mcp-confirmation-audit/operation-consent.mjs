import { confirmationState, writeAnnotations } from './confirmation-contract.mjs';

const mutations = ['exec', 'write_file'];
const writeTools = ['exec_command', 'write_file', 'queue_router_task'];
const queueTools = ['router_status', 'read_file', 'queue_diagnostic'];
export const isMutation = op => mutations.includes(op);

export function describeTool(tool) {
  const canMutate = writeTools.includes(tool.name);
  const queues = queueTools.includes(tool.name);
  const annotations = canMutate ? { ...writeAnnotations, openWorldHint: tool.name !== 'write_file' } : {
    readOnlyHint: !queues,
    destructiveHint: false,
    idempotentHint: !queues,
    openWorldHint: false,
  };
  if (!canMutate) return { ...tool, annotations };
  const inputSchema = { ...tool.inputSchema, properties: {
    ...tool.inputSchema.properties,
    confirmed: { type: 'boolean', description: 'Use true only for the exact operation the user approved. Server authorization and ChatGPT confirmation apply independently.' },
    approval_id: { type: 'string', format: 'uuid', description: 'One-time exact-operation approval from the authenticated owner channel. Required for writes and command execution.' },
  } };
  return { ...tool, annotations, inputSchema };
}

// Called within the queue storage transaction. The digest comes from the validated task.
export function consumeApproval(sql, id, digest, revision, now) {
  if (typeof id !== 'string' || !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(id)) return false;
  return sql.exec('DELETE FROM exact_consent WHERE id=? AND fingerprint=? AND revision=? AND expires>? RETURNING id',
    id, digest, revision, now).toArray().length === 1;
}

export function createConsentTables(sql) {
  sql.exec('CREATE TABLE IF NOT EXISTS exact_consent (id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, revision INTEGER NOT NULL, expires INTEGER NOT NULL)');
  sql.exec('CREATE TABLE IF NOT EXISTS operation_audit (seq INTEGER PRIMARY KEY, correlation TEXT NOT NULL, stage TEXT NOT NULL, outcome TEXT NOT NULL, at INTEGER NOT NULL)');
  sql.exec('CREATE TABLE IF NOT EXISTS operation_audit_link (job TEXT PRIMARY KEY, correlation TEXT NOT NULL, created INTEGER NOT NULL)');
}

export function auditOutcome(sql, correlation, stage, outcome, now) {
  sql.exec('INSERT INTO operation_audit(correlation,stage,outcome,at) VALUES(?,?,?,?)', correlation, stage, outcome, now);
  sql.exec('DELETE FROM operation_audit WHERE seq <= (SELECT MAX(seq)-999 FROM operation_audit) OR at<?', now - 604800000);
}

export function linkOperation(sql, job, correlation, now) {
  sql.exec('DELETE FROM operation_audit_link WHERE created<? OR job NOT IN (SELECT id FROM jobs)', now - 604800000);
  sql.exec('INSERT INTO operation_audit_link VALUES(?,?,?)', job, correlation, now);
}

export function auditLifecycle(sql, event, job, now) {
  if (!['claimed','lease_expired_unverified','result_received','manually_reconciled'].includes(event)) return;
  const row = sql.exec('SELECT correlation FROM operation_audit_link WHERE job=? AND created>=?', job, now-604800000).toArray()[0];
  if (row) auditOutcome(sql,row.correlation,'lifecycle',event,now);
}

export function mutationDenial(policy, task, arguments_) {
  if (!policy.enabled) return 'remote_disabled';
  if (!policy.scopes.includes(task.op)) return 'scope_denied';
  if (confirmationState(arguments_.confirmed) === 'invalid') return 'invalid_confirmation_argument';
  if (isMutation(task.op) && (arguments_.confirmed === false || (!policy.owner_admin && arguments_.confirmed !== true))) {
    return 'confirmation_required';
  }
  return null;
}
