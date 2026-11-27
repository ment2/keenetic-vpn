"""Official Hysteria2 MIPSLE soft-float client interop; disposable loopback only."""
import argparse,json,os,subprocess as sp,tempfile,socket,time,threading,http.server
from pathlib import Path
from loopback_lab import Witness, port, stop, run

def main():
 a=argparse.ArgumentParser()
 a.add_argument('--client',required=True);a.add_argument('--server',required=True);a.add_argument('--qemu',required=True)
 z=a.parse_args()
 assert {x['ifname'] for x in json.loads(sp.check_output(['ip','-j','link','show']))}=={'lo'}
 client=[z.qemu,z.client];run(client+['version'])
 with tempfile.TemporaryDirectory() as td:
  p=Path(td);cert=p/'ca.pem';key=p/'key.pem'
  run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost','-addext','basicConstraints=critical,CA:TRUE','-keyout',str(key),'-out',str(cert)])
  httpd=http.server.ThreadingHTTPServer(('127.0.0.1',0),Witness)
  thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start()
  udp=port(socket.SOCK_DGRAM)
  server={'listen':f'127.0.0.1:{udp}','tls':{'cert':str(cert),'key':str(key)},'auth':{'type':'password','password':'synthetic-only'},'obfs':{'type':'salamander','salamander':{'password':'synthetic-mask'}}}
  sf=p/'server.json';sf.write_text(json.dumps(server))
  srv=sp.Popen([z.server,'server','-c',str(sf)],stdout=sp.DEVNULL,stderr=sp.DEVNULL)
  try:
   end=time.monotonic()+8
   while time.monotonic()<end:
    assert srv.poll() is None
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
     try:s.bind(('127.0.0.1',udp))
     except OSError:break
    time.sleep(.1)
   else:raise RuntimeError('server bind unavailable')
   for case in ('positive','wrong_auth','wrong_tls','wrong_mask'):
    socks=port(socket.SOCK_STREAM)
    cfg={'server':f'127.0.0.1:{udp}','auth':'incorrect' if case=='wrong_auth' else 'synthetic-only','tls':{'sni':'wrong.invalid' if case=='wrong_tls' else 'localhost','ca':str(cert),'insecure':False},'obfs':{'type':'salamander','salamander':{'password':'incorrect' if case=='wrong_mask' else 'synthetic-mask'}},'socks5':{'listen':f'127.0.0.1:{socks}','disableUDP':True}}
    cf=p/'client.json';cf.write_text(json.dumps(cfg));cf.chmod(0o600)
    Witness.hits.clear()
    with (p/'client.log').open('wb') as log:
     child=sp.Popen(client+['client','-c',str(cf)],stdout=log,stderr=sp.STDOUT)
     try:
      ready=False;end=time.monotonic()+9
      while time.monotonic()<end and child.poll() is None:
       with socket.socket() as s:
        if s.connect_ex(('127.0.0.1',socks))==0:ready=True;break
       time.sleep(.1)
      if ready:
       env={k:v for k,v in os.environ.items() if k.lower() not in ('http_proxy','https_proxy','all_proxy','no_proxy')}
       r=sp.run(['curl','-q','--noproxy','','--proxy',f'socks5h://127.0.0.1:{socks}','--max-time','5','-s','-o','/dev/null','-w','%{http_code}',f'http://127.0.0.1:{httpd.server_port}/internet'],capture_output=True,env=env,timeout=7)
       ok=r.returncode==0 and r.stdout==b'204'
      else:ok=False
      if case=='positive':assert ok and Witness.hits==['/internet'],(ready,ok,Witness.hits)
      else:assert not ok and not Witness.hits,(case,ready,ok,Witness.hits)
      print('OFFICIAL_CLIENT',case,'PASS',flush=True)
     finally:stop(child)
  finally:
   stop(srv);httpd.shutdown();httpd.server_close();thread.join(timeout=3)
 print('OFFICIAL_MIPSLE_SF_LOOPBACK_PASS')
if __name__=='__main__':main()
