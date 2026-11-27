import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { resolve, dirname, join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { randomUUID } from 'node:crypto';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import test from 'node:test';

const [runtime, keenetic, ha, keeneticBase, haBase] = process.argv.slice(2);
const require = createRequire(pathToFileURL(join(resolve(runtime), 'package.json')));
const { Miniflare, convertV4MiniflareOptions } = await import(pathToFileURL(require.resolve('miniflare')));
const admin = 'synthetic-admin'.padEnd(40,'a');
const agent = 'synthetic-agent'.padEnd(40,'b');
const policy = 'synthetic-policy'.padEnd(40,'c');
const bindings = {
  CONTROL_ADMIN_TOKEN: admin, CONTROL_AGENT_TOKEN: agent, CONTROL_POLICY_TOKEN: policy,
  CONTROL_DATA_KEY: 'ab'.repeat(32),
};

for (const [name, entry, root, prefix, baseline] of [
  ['Keenetic', keenetic, resolve(dirname(keenetic),'..'), '', keeneticBase],
  ['HA RC5', ha, resolve(dirname(ha)), 'ha_', haBase],
]) test(name + ' native workerd', async t => {
  let outbound = 0;
  const persistence = mkdtempSync(join(tmpdir(),'operation-consent-'));
  const modules = (prefix
    ? ['rc5.mjs','operation-consent.mjs','confirmation-contract.mjs']
    : ['src/worker.mjs','src/coordinator.mjs','src/security.mjs','src/readiness-proof.mjs',
      'src/operation-consent.mjs','src/confirmation-contract.mjs','mobile-tools.mjs','reference/worker-v4.js'])
    .map(path => ({type:'ESModule',path:join(root,path),contents:readFileSync(join(root,path),'utf8')}));
  const options = modules => convertV4MiniflareOptions({
    name: 'consent-local', host: '127.0.0.1', port: 0, cf: false, unsafeRegisterWorker: false,
    modules, modulesRoot: root, compatibilityDate: '2026-11-04',
    bindings: { ...bindings, ...(prefix ? { TARGET_DEVICE: 'homeassistant' } : {}) },
    durableObjects: { CONTROL_QUEUE: { className: 'QueueCoordinator', useSQLite: true } },
    resourcePersistencePath: persistence,
    outboundService: () => { outbound++; return new Response(null,{status:503}); },
  });
  const host = new Miniflare(options(modules));
  t.after(async () => {
    await host.dispose();
    rmSync(persistence,{recursive:true,force:true});
    assert.equal(outbound, 0);
  });
  const request = (path, body, { owner = false, token = admin, key } = {}) => host.dispatchFetch('https://synthetic.invalid'+path, {
    method: body === undefined ? 'GET' : 'POST',
    headers: { authorization: 'Bearer ' + token, 'content-type': 'application/json',
      ...(owner ? { 'x-control-policy-token': policy } : {}), ...(key ? { 'idempotency-key': key } : {}) },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  const rpc = async (method, params) => (await request('/mcp',{jsonrpc:'2.0',id:1,method,params})).json();
  const task = {op:'write_file',path:'/synthetic-unit/sample.txt',content:'synthetic-fixture-value'};
  const input = {path:task.path,content:task.content};
  const write = async args => (await rpc('tools/call',{name:prefix+'write_file',arguments:args})).result.structuredContent;
  const setPolicy = async (owner_admin_enabled, scopes=['write_file']) => {
    assert.equal((await request('/v1/owner/permissions',{remote_enabled:true,owner_admin_enabled,scopes},{owner:true})).status,200);
  };
  const approve = async () => {
    const response = await request('/v1/owner/approve-operation',{...task,confirmed:true},{owner:true});
    assert.equal(response.status,201);
    return (await response.json()).approval_id;
  };
  const tools = (await rpc('tools/list')).result.tools;
  const spec = tools.find(tool => tool.name === prefix+'write_file');
  assert.deepEqual(spec.annotations,{readOnlyHint:false,destructiveHint:true,idempotentHint:false,openWorldHint:false});
  assert.equal(tools.find(tool=>tool.name===prefix+'exec_command').annotations.openWorldHint,true);
  for (const tool of tools) {
    for (const key of ['readOnlyHint','destructiveHint','openWorldHint','idempotentHint']) assert.equal(typeof tool.annotations[key],'boolean');
  }
  if (prefix) {
    assert.deepEqual(spec.securitySchemes,[{type:'oauth2',scopes:['ha:control']}]);
    assert.deepEqual(spec._meta.securitySchemes,spec.securitySchemes);
  }
  assert.equal(spec.inputSchema.properties.confirmed.type,'boolean');
  assert.equal(spec.inputSchema.properties.approval_id.type,'string');
  await setPolicy(true);
  assert.equal((await request('/v1/owner/approve-operation',{...task,confirmed:true})).status,401);
  assert.equal((await request('/v1/owner/approve-operation',{...task,confirmed:'true'},{owner:true})).status,400);
  assert.equal((await write({...input,confirmed:'true'})).error,'invalid_confirmation_argument');
  assert.equal((await write({...input,confirmed:true})).error,'exact_operation_approval_required');
  const approval_id = await approve();
  assert.equal((await write({...input,content:'different',approval_id})).error,'exact_operation_approval_required');
  const attempts = await Promise.all([write({...input,approval_id}),write({...input,approval_id})]);
  assert.equal(attempts.filter(result => result.status==='queued').length,1);
  assert.equal(attempts.filter(result => result.error==='exact_operation_approval_required').length,1);
  const claimed = await request('/v1/agent/next',undefined,{token:agent});
  assert.equal(claimed.status,200);
  const job = await claimed.json();
  assert.equal(job.content,task.content);
  assert.equal((await request('/v1/agent/result/'+job.id,{lease_id:job.lease_id,exit_code:0,output:'synthetic-agent-output'},{token:agent})).status,200);
  const old = await approve();
  await setPolicy(false);
  assert.equal((await write({...input,approval_id:old,confirmed:true})).error,'exact_operation_approval_required');
  const current = await approve();
  assert.equal((await write({...input,approval_id:current,confirmed:false})).error,'confirmation_required');
  const viaRest = await request('/v1/jobs',{...task,approval_id:current,confirmed:true},{key:randomUUID()});
  assert.equal(viaRest.status,202);
  await setPolicy(true,[]);
  assert.equal((await write({...input,confirmed:true})).error,'scope_denied');
  assert.equal((await request('/v1/owner/operation-audit')).status,401);
  const {events} = await (await request('/v1/owner/operation-audit',undefined,{owner:true})).json();
  assert.ok(events.length >= 24 && events.length <= 100);
  const groups = Map.groupBy(events,event => event.correlation);
  for (const group of groups.values()) {
    assert.deepEqual(group.filter(event => event.stage!=='lifecycle').map(event => event.stage).sort(),['decision','received','result']);
    for (const event of group) assert.deepEqual(Object.keys(event).sort(),['at','correlation','outcome','stage']);
  }
  const lifecycle = [...groups.values()].find(group => group.some(event => event.outcome==='claimed'));
  assert.ok(lifecycle.some(event => event.outcome==='result_received'));
  for (const value of [task.path,task.content,approval_id,old,current,admin,policy,job.id,'synthetic-agent-output']) {
    assert.ok(!JSON.stringify(events).includes(value));
  }
  assert.ok(baseline,'Supply a pristine baseline for the same-storage rollback test');
  const baselineModules = modules.filter(module => !/(?:operation-consent|confirmation-contract)[.]mjs$/.test(module.path))
    .map(module => {
      const local = module.path===resolve(entry) && prefix ? baseline
        : !prefix && /(?:worker|coordinator)[.]mjs$/.test(module.path) ? join(baseline,module.path.split(/[\\/]/).at(-1))
        : null;
      return local ? {...module,contents:readFileSync(local,'utf8')} : module;
    });
  await host.setOptions(options(baselineModules));
  assert.equal((await request('/v1/owner/operation-audit',undefined,{owner:true})).status,404);
  const preserved = await (await request('/v1/jobs/'+job.id)).json();
  assert.equal(preserved.status,'done');
  assert.equal(preserved.output,'synthetic-agent-output');
  await host.setOptions(options(modules));
  assert.equal((await request('/v1/owner/operation-audit',undefined,{owner:true})).status,200);
});
