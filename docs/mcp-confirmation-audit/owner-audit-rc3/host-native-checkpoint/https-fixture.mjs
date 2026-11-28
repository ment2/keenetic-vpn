// Test-only, single-process HTTPS adapter. No production routes or bindings.
import {createServer} from 'node:https';
import {readFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
import {createFixture} from './server.mjs';
const MAX=8192, WINDOW=20*60*1000;
export function lab({tls,hostname,ttlMs=WINDOW,now=Date.now,onEvent=()=>{}}){
  if(typeof hostname!=='string'||!hostname||!Number.isInteger(ttlMs)||ttlMs<1000||ttlMs>WINDOW)throw Error('invalid_lab_config');
  const start=now(),fixture=createFixture();
  let received=0,accepted=0;
  const status=()=>Object.freeze({received,accepted,expired:now()-start>=ttlMs});
  const reply=(res,n,body='')=>{res.writeHead(n,{'Content-Type':'application/json','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});res.end(body)};
  const server=createServer({...tls,minVersion:'TLSv1.2',maxHeaderSize:8192},async(req,res)=>{
    try{
      if(status().expired){req.resume();return reply(res,410)}
      if(req.headers.host!==hostname){req.resume();return reply(res,421)}
      if(req.url!=='/mcp'){req.resume();return reply(res,404)}
      if(req.method!=='POST'){req.resume();return reply(res,405)}
      if(!/^application\/json(?:\s*;|$)/i.test(req.headers['content-type']??'')){req.resume();return reply(res,415)}
      const len=req.headers['content-length'];if(len!==undefined&&(!/^\d+$/.test(len)||Number(len)>MAX)){req.resume();return reply(res,413)}
      let total=0;const chunks=[];
      for await(const b of req){total+=b.length;if(total>MAX){reply(res,413);return}chunks.push(b)}
      const body=Buffer.concat(chunks);let rpc;try{rpc=JSON.parse(body)}catch{return reply(res,400)}
      if(status().expired)return reply(res,410);
      const mutation=rpc?.jsonrpc==='2.0'&&rpc?.method==='tools/call'&&rpc?.params?.name==='synthetic_replace_marker';
      // Limit even malformed mutation attempts; do not retain arguments, IDs, headers or IPs.
      if(mutation){if(received>=20)return reply(res,429);received++;onEvent({stage:'received',count:received})}
      const out=await fixture(new Request('https://fixture.invalid/mcp',{method:'POST',headers:{'Content-Type':'application/json'},body}));
      const text=await out.text();if(mutation&&out.ok&&text){let r;try{r=JSON.parse(text)}catch{}if(r?.result?.structuredContent&&!r.error){accepted++;onEvent({stage:'accepted',count:accepted})}}
      reply(res,out.status,text);
    }catch{if(!res.headersSent)reply(res,400);else res.end()}
  });
  server.requestTimeout=10000;server.headersTimeout=5000;server.keepAliveTimeout=2000;server.maxConnections=8;
  return {server,status};
}
if(process.argv[1]&&pathToFileURL(process.argv[1]).href===import.meta.url){
  // The host and certificate must be provisioned by an authorized test-host operator.
  // Bind loopback by default; public hosting must be deliberately enabled on a dedicated test host.
  const {LAB_TLS_KEY,LAB_TLS_CERT,LAB_HOST,LAB_BIND='127.0.0.1',LAB_PORT='8443'}=process.env;
  if(!LAB_TLS_KEY||!LAB_TLS_CERT||!LAB_HOST||!/^\d+$/.test(LAB_PORT))throw Error('missing_lab_configuration');
  const port=Number(LAB_PORT);if(port<1||port>65535)throw Error('invalid_port');
  if(!['127.0.0.1','::1'].includes(LAB_BIND)&&process.env.LAB_DEDICATED_TEST_HOST_APPROVED!=='yes')throw Error('dedicated_test_host_approval_required');
  const service=lab({tls:{key:readFileSync(LAB_TLS_KEY),cert:readFileSync(LAB_TLS_CERT)},hostname:LAB_HOST,onEvent:e=>console.log(JSON.stringify(e))});
  service.server.listen(port,LAB_BIND,()=>console.log('SYNTHETIC_LAB_READY'));
  setTimeout(()=>{service.server.close();service.server.closeAllConnections();},WINDOW).unref();
}
