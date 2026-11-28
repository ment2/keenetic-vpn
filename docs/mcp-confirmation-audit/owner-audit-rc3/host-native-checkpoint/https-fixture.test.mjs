import {test} from 'node:test';
import assert from 'node:assert/strict';
import {request} from 'node:https';
import {readFileSync} from 'node:fs';
import {lab} from './https-fixture.mjs';
const [key,cert]=process.argv.slice(2).map(p=>readFileSync(p));
let now=0;const events=[];
const h=lab({tls:{key,cert},hostname:'localhost',ttlMs:1000,now:()=>now,onEvent:e=>events.push(e)});
await new Promise((ok,fail)=>{h.server.once('error',fail);h.server.listen(0,'127.0.0.1',ok)});
const port=h.server.address().port;
const rpc=(name,args={})=>({jsonrpc:'2.0',id:1,method:'tools/call',params:{name,arguments:args}});
function req({body,path='/mcp',method='POST',host='localhost',type='application/json',trust=true}={}){return new Promise((ok,fail)=>{const bytes=Buffer.from(typeof body==='string'?body:JSON.stringify(body??rpc('synthetic_status')));const r=request({hostname:'127.0.0.1',servername:'localhost',port,path,method,ca:trust?cert:undefined,rejectUnauthorized:true,headers:{Host:host,'Content-Type':type,'Content-Length':bytes.length}},res=>{const chunks=[];res.on('data',x=>chunks.push(x));res.on('end',()=>{const text=Buffer.concat(chunks).toString();ok({status:res.statusCode,value:text?JSON.parse(text):null})})});r.on('error',fail);r.end(bytes)})}
try{
 await test('TLS verified, no untrusted certificate accepted',async()=>{assert.equal((await req()).status,200);await assert.rejects(req({trust:false}));});
 await test('no non-MCP routes or foreign Host',async()=>{assert.equal((await req({path:'/v1/jobs'})).status,404);assert.equal((await req({host:'unapproved.invalid'})).status,421);assert.equal((await req({method:'GET'})).status,405);});
 await test('invalid content type or oversized body rejected without mutation',async()=>{assert.equal((await req({type:'text/plain'})).status,415);assert.equal((await req({body:'x'.repeat(8193)})).status,413);assert.deepEqual(h.status(),{received:0,accepted:0,expired:false});});
 await test('catalog and actual HTTPS marker replacement, only redacted counter events',async()=>{const list=(await req({body:{jsonrpc:'2.0',id:1,method:'tools/list'}})).value.result.tools;assert.equal(list.length,2);assert.equal(list.find(x=>x.name==='synthetic_replace_marker').annotations.destructiveHint,true);const before=(await req()).value.result.structuredContent;assert.deepEqual(before,{marker:'ALPHA',mutations:0});const bad=await req({body:rpc('synthetic_replace_marker',{marker:'INVALID'})});assert.equal(bad.value.error.code,-32602);const after=(await req({body:rpc('synthetic_replace_marker',{marker:'BETA'})})).value.result.structuredContent;assert.deepEqual(after,{marker:'BETA',mutations:1});assert.deepEqual(events,[{stage:'received',count:1},{stage:'received',count:2},{stage:'accepted',count:1}]);});
 await test('TTL expiration fails closed and does not change counters',async()=>{now=1000;assert.equal((await req({body:rpc('synthetic_replace_marker',{marker:'ALPHA'})})).status,410);assert.deepEqual(h.status(),{received:2,accepted:1,expired:true});});
}finally{await new Promise(resolve=>{h.server.close(resolve);h.server.closeAllConnections()})}
