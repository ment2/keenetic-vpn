import {test} from 'node:test';
import assert from 'node:assert/strict';
import {decideWrite, auditRecord, writeAnnotations, confirmationDescription} from './confirmation-contract.mjs';
function historical(p,c) {
  if (!p.enabled) return [false,'remote_disabled'];
  if (!p.scopes.includes('write_file')) return [false,'scope_denied'];
  if (!p.owner_admin && c!==true) return [false,'confirmation_required'];
  return [true,p.owner_admin?'server_owner_grant':'caller_asserted_exact_approval'];
}
for (const enabled of [0,1]) for (const owner_admin of [0,1]) for (const scoped of [false,true]) for (const c of [undefined,false,true]) {
  test(`historical parity enabled=${enabled} owner=${owner_admin} scope=${scoped} confirmed=${c}`,()=>{
    const p={enabled,owner_admin,scopes:scoped?['write_file']:['read_file']};
    const d=decideWrite(p,c);
    assert.deepEqual([d.allowed,d.reason],historical(p,c));
  });
}
const allowed={enabled:1,owner_admin:1,scopes:['write_file']};
for(const c of ['true',1,null,{},[]]) test(`reject malformed confirmation ${JSON.stringify(c)}`,()=>assert.equal(decideWrite(allowed,c).reason,'invalid_confirmation_argument'));
for(const p of [null,{...allowed,enabled:'true'},{...allowed,owner_admin:'false'},{...allowed,scopes:'write_file'}]) test('reject malformed policy '+JSON.stringify(p),()=>assert.equal(decideWrite(p,true).reason,'invalid_policy'));
test('annotations unchanged; no automatic confirmation',()=>{assert.deepEqual(writeAnnotations,{readOnlyHint:false,destructiveHint:true,idempotentHint:false,openWorldHint:true});assert.match(confirmationDescription,/Do not infer/);});
test('audit has no payload, path, auth header, content or host approval claim',()=>{
  const rec=auditRecord(decideWrite(allowed,undefined),'12345678-1234-1234-1234-123456789abc',2);
  assert.deepEqual(Object.keys(rec).sort(),['allowed','confirmation_argument','correlation_id','event','host_approval','operation','reason','revision'].sort());
  assert.equal(rec.host_approval,'not_observable');assert.equal(rec.confirmation_argument,'absent');
});
test('caller assertion is not evidence of host approval',()=>{
  const rec=auditRecord(decideWrite({...allowed,owner_admin:0},true),'12345678-1234-1234-1234-123456789abc',2);
  assert.equal(rec.reason,'caller_asserted_exact_approval');assert.equal(rec.host_approval,'not_observable');
});
test('audit rejects raw user correlation or invalid revision',()=>{assert.throws(()=>auditRecord(decideWrite(allowed,true),'private-path',2));assert.throws(()=>auditRecord(decideWrite(allowed,true),'12345678-1234-1234-1234-123456789abc',-1));});
