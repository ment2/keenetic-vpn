// Offline candidate, not an installed MCP or proof of host approval.
// This helper is for an authenticated coordinator, AFTER schema validation.
export const writeAnnotations = Object.freeze({readOnlyHint:false, destructiveHint:true, idempotentHint:false, openWorldHint:true});
export const confirmationDescription = 'Set true only after the user explicitly approves this exact path and content. Do not infer this from owner_admin or a standing grant. An omitted or false value does not assert approval. ChatGPT host approval and server authorization remain independent; do not retry rejected or uncertain operations.';
export const writeDescription = 'Queue an owner-authorized UTF-8 file write that may overwrite existing data. The server independently checks remote enablement and the write_file scope. An active server-side owner grant or an exact operation approval is required by server policy. This does not substitute for any ChatGPT approval. Returns a job ID; poll only that job.';
export function confirmationState(value) {
  return value === undefined ? 'absent' : value === true ? 'asserted' : value === false ? 'not_asserted' : 'invalid';
}
export function decideWrite(p, confirmed) {
  const state = confirmationState(confirmed);
  const result = (allowed, reason, status) => Object.freeze({allowed, reason, status, confirmation_argument:state});
  // Match archived coordinator behavior for valid boolean/omitted inputs.
  // Only accept policy values produced by the DB (0/1) or its boolean mapping.
  if (!p || ![0,1,false,true].includes(p.enabled) || ![0,1,false,true].includes(p.owner_admin) || !Array.isArray(p.scopes)) return result(false,'invalid_policy',503);
  if (!p.enabled) return result(false,'remote_disabled',403);
  if (!p.scopes.includes('write_file')) return result(false,'scope_denied',403);
  if (state === 'invalid') return result(false,'invalid_confirmation_argument',400);
  if (!p.owner_admin && confirmed !== true) return result(false,'confirmation_required',403);
  return result(true,p.owner_admin ? 'server_owner_grant' : 'caller_asserted_exact_approval',202);
}
// Do not label caller_asserted_exact_approval as verified host/user approval.
// Use a server-generated correlation ID and trusted policy revision only.
export function auditRecord(decision, correlation, revision) {
  if (typeof correlation !== 'string' || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(correlation) || !Number.isSafeInteger(revision) || revision < 0) throw new TypeError('invalid audit metadata');
  if (!['invalid_policy','remote_disabled','scope_denied','invalid_confirmation_argument','confirmation_required','server_owner_grant','caller_asserted_exact_approval'].includes(decision.reason) || !['absent','asserted','not_asserted','invalid'].includes(decision.confirmation_argument) || typeof decision.allowed !== 'boolean') throw new TypeError('invalid decision');
  return {event:'write_authorization_decision',operation:'write_file',correlation_id:correlation,revision,allowed:decision.allowed,reason:decision.reason,confirmation_argument:decision.confirmation_argument,host_approval:'not_observable'};
}
