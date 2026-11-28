// Standalone synthetic MCP server. No shell, disk or device operations; no production bindings.
// This module stores only a fixed test marker in process memory. Host approval must be tested separately.
const variants=['ALPHA','BETA'];
const schema={type:'object',properties:{marker:{type:'string',enum:variants}},required:['marker'],additionalProperties:false};
const statusSchema={type:'object',properties:{marker:{type:'string',enum:variants},mutations:{type:'integer',minimum:0}},required:['marker','mutations'],additionalProperties:false};
export const tools=[{name:'synthetic_status',title:'Read synthetic test marker',description:'Read the disposable test marker and count of accepted replacements. No real device or file access.',inputSchema:{type:'object',properties:{},additionalProperties:false},outputSchema:statusSchema,annotations:{readOnlyHint:true,destructiveHint:false,openWorldHint:false,idempotentHint:true},securitySchemes:[{type:'noauth'}]}, {name:'synthetic_replace_marker',title:'Replace synthetic test marker',description:'Overwrite the disposable test marker in memory. Increments the replacement counter. Request explicit user approval through the host before calling. No real device, file, shell or network access.',inputSchema:schema,outputSchema:statusSchema,annotations:{readOnlyHint:false,destructiveHint:true,openWorldHint:false,idempotentHint:false},securitySchemes:[{type:'noauth'}]}];
export function createFixture(){let marker='ALPHA',mutations=0;return async request=>{
 const url=new URL(request.url);if(url.pathname!=='/mcp')return new Response(null,{status:404});if(request.method==='GET')return new Response(null,{status:405});if(request.method!=='POST')return new Response(null,{status:405});
 let b;try{const reader=request.body.getReader(),dec=new TextDecoder();let n=0,s='';for(;;){const x=await reader.read();if(x.done)break;if((n+=x.value.length)>8192){await reader.cancel();return new Response(null,{status:413});}s+=dec.decode(x.value,{stream:true});}b=JSON.parse(s+dec.decode());}catch{return new Response(null,{status:400});}
 const reply=v=>Response.json({jsonrpc:'2.0',id:b?.id??null,...v},{headers:{'Cache-Control':'no-store'}});const error=(code,message)=>reply({error:{code,message}});const ok=result=>reply({result});
 if(!b||Array.isArray(b)||b.jsonrpc!=='2.0'||typeof b.method!=='string')return error(-32600,'Invalid request');
 if(b.id===undefined)return new Response(null,{status:202});
 if(b.method==='initialize')return ok({protocolVersion:['2025-03-26','2025-06-18','2025-11-25'].includes(b.params?.protocolVersion)?b.params.protocolVersion:'2025-03-26',capabilities:{tools:{listChanged:false}},serverInfo:{name:'synthetic-consent-lab',version:'0.1.0'}});
 if(b.method==='ping')return ok({});if(b.method==='tools/list')return ok({tools});if(b.method!=='tools/call')return error(-32601,'Unknown method');
 const a=b.params?.arguments??{};if(!a||typeof a!=='object'||Array.isArray(a))return error(-32602,'Invalid arguments');
 if(b.params?.name==='synthetic_status'){if(Object.keys(a).length)return error(-32602,'Invalid arguments');}
 else if(b.params?.name==='synthetic_replace_marker'){if(Object.keys(a).length!==1||!variants.includes(a.marker))return error(-32602,'Invalid marker');if(mutations>=1000)return error(-32000,'Fixture capacity');marker=a.marker;mutations++;}
 else return error(-32601,'Unknown tool');
 const value={marker,mutations};return ok({structuredContent:value,content:[{type:'text',text:JSON.stringify(value)}]});
 };}
export default {fetch:createFixture()};
