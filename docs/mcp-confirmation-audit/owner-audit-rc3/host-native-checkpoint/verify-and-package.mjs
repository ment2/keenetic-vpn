// Build a portable manifest only after an operator approves a dedicated synthetic HTTPS endpoint.
// This helper sends three read-only MCP protocol requests, not a mutating tool call.
import {readFileSync,mkdirSync,writeFileSync} from 'node:fs';
import {join} from 'node:path';
const [endpoint,out]=process.argv.slice(2);
if(!endpoint||!out||process.env.LAB_DEDICATED_ENDPOINT_APPROVED!=='yes')throw Error('owner_approved_dedicated_endpoint_required');
const u=new URL(endpoint);
if(u.protocol!=='https:'||u.username||u.password||u.search||u.hash||u.pathname!=='/mcp'||u.href!==endpoint)throw Error('exact_https_mcp_url_required');
let id=0;
async function call(method,params={}){
 const n=++id;const res=await fetch(endpoint,{method:'POST',redirect:'error',headers:{'Content-Type':'application/json','Accept':'application/json, text/event-stream','MCP-Protocol-Version':'2025-03-26'},body:JSON.stringify({jsonrpc:'2.0',id:n,method,params}),signal:AbortSignal.timeout(10000)});
 if(!res.ok||!res.headers.get('content-type')?.includes('application/json'))throw Error('unexpected_mcp_response');
 const reader=res.body.getReader(),chunks=[];let total=0;for(;;){const x=await reader.read();if(x.done)break;if((total+=x.value.length)>16384){await reader.cancel();throw Error('response_too_large')}chunks.push(x.value)}
 const v=JSON.parse(Buffer.concat(chunks).toString());if(v.id!==n||v.error||!v.result)throw Error('invalid_mcp_response');return v.result;
}
const init=await call('initialize',{protocolVersion:'2025-03-26',capabilities:{},clientInfo:{name:'consent-lab-readonly-preflight',version:'1.0'}});
if(init.serverInfo?.name!=='synthetic-consent-lab')throw Error('wrong_server_identity');
const list=(await call('tools/list')).tools;
const expected={synthetic_status:{readOnlyHint:true,destructiveHint:false,openWorldHint:false,idempotentHint:true},synthetic_replace_marker:{readOnlyHint:false,destructiveHint:true,openWorldHint:false,idempotentHint:false}};
if(!Array.isArray(list)||list.length!==2||new Set(list.map(t=>t.name)).size!==2||list.some(t=>!Object.hasOwn(expected,t.name)||Object.keys(expected[t.name]).some(k=>t.annotations?.[k]!==expected[t.name][k])))throw Error('unexpected_tool_catalog');
const baseline=(await call('tools/call',{name:'synthetic_status',arguments:{}})).structuredContent;
if(baseline?.marker!=='ALPHA'||baseline.mutations!==0)throw Error('fixture_not_fresh');
// A private plugin is not the same as a private network endpoint. The operator must
// attest the separate host, access controls and lifetime independently; the response cannot prove these.
const manifest=JSON.parse(readFileSync(new URL('./plugin.json',import.meta.url),'utf8'));
mkdirSync(out,{recursive:false});writeFileSync(join(out,'plugin.json'),JSON.stringify(manifest,null,2)+'\n',{flag:'wx'});
writeFileSync(join(out,'mcp.json'),JSON.stringify({$schema:'https://agent-plugins.org/schemas/1.0.0/mcp.schema.json',mcpServers:{'synthetic-consent-lab':{type:'streamable-http',url:endpoint,extensions:{'com.openai':{auth:{type:'none'}}}}}},null,2)+'\n',{flag:'wx'});
console.log('READONLY_PREFLIGHT_PASS: two tools, fresh marker, descriptor match; registration and actual host approval still pending');
