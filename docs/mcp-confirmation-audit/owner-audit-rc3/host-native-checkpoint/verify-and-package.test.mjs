import {test} from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {readFileSync,mkdtempSync,rmSync,existsSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createServer} from 'node:https';
import {createFixture} from './server.mjs';
const [keyPath,certPath]=process.argv.slice(2);
const root=mkdtempSync(join(tmpdir(),'synthetic-plugin-check-'));
const fixture=createFixture();
let calls=[];
const server=createServer({key:readFileSync(keyPath),cert:readFileSync(certPath)},async(req,res)=>{try{const chunks=[];for await(const x of req)chunks.push(x);const body=Buffer.concat(chunks);const data=JSON.parse(body);calls.push(data.method==='tools/call'?data.params.name:data.method);const r=await fixture(new Request('https://fixture.invalid/mcp',{method:'POST',headers:{'content-type':'application/json'},body}));res.writeHead(r.status,{'content-type':'application/json'});res.end(await r.text())}catch{res.writeHead(400);res.end()}});
await new Promise((ok,fail)=>{server.once('error',fail);server.listen(0,'127.0.0.1',ok)});
const endpoint='https://localhost:'+server.address().port+'/mcp';
function run(url,out,approved){return new Promise((resolve,reject)=>{const p=spawn(process.execPath,[fileURLToPath(new URL('./verify-and-package.mjs',import.meta.url)),url,out],{env:{...process.env,NODE_EXTRA_CA_CERTS:certPath,LAB_DEDICATED_ENDPOINT_APPROVED:approved},stdio:['ignore','pipe','pipe']});let outText='';p.stdout.on('data',x=>outText+=x);p.stderr.on('data',()=>{});p.once('error',reject);p.once('exit',code=>resolve({code,outText}));})}
try{
 await test('no explicit dedicated endpoint approval means no request or package',async()=>{const out=join(root,'denied');assert.notEqual((await run(endpoint,out,'no')).code,0);assert.equal(calls.length,0);assert.equal(existsSync(out),false)});
 await test('invalid non-HTTPS URL refused before access',async()=>{const out=join(root,'bad-url');assert.notEqual((await run(endpoint.replace('https:','http:'),out,'yes')).code,0);assert.equal(calls.length,0);assert.equal(existsSync(out),false)});
 await test('fresh dedicated loopback HTTPS fixture creates exact portable config using only reads',async()=>{const out=join(root,'approved');const result=await run(endpoint,out,'yes');assert.equal(result.code,0);assert.match(result.outText,/READONLY_PREFLIGHT_PASS/);assert.deepEqual(calls,['initialize','tools/list','synthetic_status']);const manifest=JSON.parse(readFileSync(join(out,'mcp.json'),'utf8'));assert.deepEqual(manifest.mcpServers['synthetic-consent-lab'],{type:'streamable-http',url:endpoint,extensions:{'com.openai':{auth:{type:'none'}}}});assert.equal(JSON.parse(readFileSync(join(out,'plugin.json'),'utf8')).name,'synthetic-consent-lab')});
}finally{await new Promise(ok=>{server.close(ok);server.closeAllConnections()});rmSync(root,{recursive:true,force:true})}
