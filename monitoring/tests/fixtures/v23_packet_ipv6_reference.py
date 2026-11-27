#!/usr/bin/env python3
"""Real IPv6 packet reference in three disposable CI network namespaces.

Independent ingress wire witness (AF_PACKET), application echo, per-protocol
DROP counters. No production interfaces, routes, rules or external endpoints.
Does not certify Keenetic vendor chains, TPROXY death path or router DNS.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid

SERVER=r'''
import socket,selectors
sel=selectors.DefaultSelector()
for typ,port in ((socket.SOCK_STREAM,18080),(socket.SOCK_DGRAM,18081),(socket.SOCK_DGRAM,53),(socket.SOCK_STREAM,53)):
 s=socket.socket(socket.AF_INET6,typ);s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);s.bind(("fd23:19::2",port))
 if typ==socket.SOCK_STREAM:s.listen(16)
 sel.register(s,selectors.EVENT_READ,(typ,port))
print("READY",flush=True)
while True:
 for key,_ in sel.select(1):
  typ,port=key.data;s=key.fileobj
  if typ==socket.SOCK_STREAM:
   c,_=s.accept()
   with c:
    c.settimeout(1);b=c.recv(4096)
    if b:print("RECEIPT",port,b.hex(),flush=True);c.sendall(b)
  else:
   b,a=s.recvfrom(4096)
   if b:print("RECEIPT",port,b.hex(),flush=True);s.sendto(b,a)
'''
WIRE=r'''
import socket,struct
s=socket.socket(socket.AF_PACKET,socket.SOCK_RAW,socket.htons(3));s.bind(("s0",0))
target=socket.inet_pton(socket.AF_INET6,"fd23:19::2")
print("READY",flush=True)
while True:
 b=s.recv(65535)
 if len(b)<58 or b[12:14]!=b"\x86\xdd" or b[38:54]!=target:continue
 proto=b[20]
 if proto not in (6,17):continue
 src,dst=struct.unpack("!HH",b[54:58])
 if dst in (53,18080,18081):print("WIRE",proto,src,dst,flush=True)
'''
CLIENT=r'''
import socket,sys,struct
phase,kind,token,source=sys.argv[1:]
dns=kind.startswith("dns");tcp=kind in ("tcp","dns_tcp")
port=53 if dns else (18080 if tcp else 18081)
if dns:
 labels=[token.encode(),b"fixture",b"invalid"]
 payload=b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"+b"".join(bytes([len(x)])+x for x in labels)+b"\x00\x00\x01\x00\x01"
 if tcp:payload=struct.pack("!H",len(payload))+payload
else:payload=token.encode()
s=socket.socket(socket.AF_INET6,socket.SOCK_STREAM if tcp else socket.SOCK_DGRAM)
s.settimeout(4 if phase=="allow" else .75);s.bind(("::",int(source)))
try:
 s.connect(("fd23:19::2",port));s.sendall(payload);b=s.recv(4096)
 if phase!="allow" or b!=payload:raise SystemExit(2)
except (TimeoutError,ConnectionError,OSError):
 if phase=="allow":raise
finally:s.close()
print(payload.hex(),flush=True)
'''
def main():
 if os.environ.get("GITHUB_ACTIONS")!="true" or os.geteuid()!=0:raise SystemExit("disposable CI root required")
 suffix=uuid.uuid4().hex[:6]
 client,router,sink=["v6"+x+suffix for x in "crs"]
 created=[];children=[]
 def run(*a):
  r=subprocess.run(a,text=True,capture_output=True,timeout=10)
  if r.returncode:
   print("FIXTURE_COMMAND_FAILED",a[0],r.returncode,r.stderr,flush=True)
   raise RuntimeError("fixture command failed")
  return r.stdout
 def ip(n,*a):return run("ip","-n",n,*a)
 def ns(n,*a):return run("ip","netns","exec",n,*a)
 kinds=(("tcp","tcp",18080),("udp","udp",18081),("dns_udp","udp",53),("dns_tcp","tcp",53))
 with tempfile.TemporaryDirectory(prefix="v23-ipv6-") as tmp:
  app=Path(tmp)/"app";wire=Path(tmp)/"wire"
  try:
   for n in (client,router,sink):
    run("ip","netns","add",n);created.append(n);ns(n,"sysctl","-qw","net.ipv6.conf.all.disable_ipv6=0","net.ipv6.conf.default.disable_ipv6=0");ip(n,"link","set","lo","up")
   ip(client,"link","add","c0","type","veth","peer","name","r0","netns",router)
   ip(router,"link","add","r1","type","veth","peer","name","s0","netns",sink)
   for n,dev,addr in ((client,"c0","fd23:18::2/64"),(router,"r0","fd23:18::1/64"),(router,"r1","fd23:19::1/64"),(sink,"s0","fd23:19::2/64")):
    ip(n,"link","set",dev,"up");ns(n,"sysctl","-qw","net.ipv6.conf."+dev+".disable_ipv6=0");ip(n,"-6","addr","add",addr,"dev",dev,"nodad")
   ip(client,"-6","route","add","fd23:19::/64","via","fd23:18::1")
   ip(sink,"-6","route","add","fd23:18::/64","via","fd23:19::1")
   ns(router,"sysctl","-qw","net.ipv6.conf.all.forwarding=1")
   for chain in ("FORWARD","OUTPUT"):ns(router,"ip6tables","-P",chain,"ACCEPT")
   # Explicit neighbor/route positive control before using application probes.
   ns(client,"ping","-6","-c","1","-W","3","fd23:19::2")
   ns(router,"ping","-6","-c","1","-W","3","fd23:19::2")
   for path,source in ((app,SERVER),(wire,WIRE)):
    with path.open("w") as f:children.append(subprocess.Popen(["ip","netns","exec",sink,sys.executable,"-u","-c",source],stdout=f,stderr=f))
   for _ in range(50):
    if all("READY" in p.read_text() for p in (app,wire)):break
    if any(c.poll() is not None for c in children):raise RuntimeError("sentinel failed")
    time.sleep(.1)
   else:raise RuntimeError("sentinel not ready")
   positive=[];negative=[]
   for phase,base,records in (("allow",32100,positive),("deny",32200,negative)):
    if phase=="deny":
     for chain in ("FORWARD","OUTPUT"):
      for kind,proto,port in kinds:
       ns(router,"ip6tables","-I",chain,"1","-o","r1","-p",proto,"--dport",str(port),"-m","comment","--comment",kind,"-j","DROP")
    for idx,(n,chain) in enumerate(((client,"FORWARD"),(router,"OUTPUT"))):
     for i,(kind,proto,port) in enumerate(kinds):
      source=base+idx*10+i
      payload=ns(n,sys.executable,"-c",CLIENT,phase,kind,uuid.uuid4().hex,str(source)).strip()
      records.append((payload,"WIRE %d %d %d"%(6 if proto=="tcp" else 17,source,port),chain,kind))
   time.sleep(.2)
   a=app.read_text();w=set(wire.read_text().splitlines())
   assert all(payload in a and packet in w for payload,packet,_,_ in positive)
   assert not any(payload in a or packet in w for payload,packet,_,_ in negative)
   assert all(c.poll() is None for c in children)
   for chain in ("FORWARD","OUTPUT"):
    lines=ns(router,"ip6tables","-L",chain,"-xvn").splitlines()
    for kind,_,_ in kinds:
     match=[l.split() for l in lines if "DROP" in l and "/* "+kind+" */" in l]
     assert len(match)==1 and int(match[0][0])>=1
     print("V6_DROP",chain,kind,match[0][0],flush=True)
   print("V6_POSITIVE_APP_AND_WIRE",len(positive),"V6_NEGATIVE_APP_AND_WIRE",0,"ATTEMPTS",len(negative),flush=True)
  finally:
   for p in children:
    if p.poll() is None:p.terminate()
    try:p.wait(timeout=3)
    except subprocess.TimeoutExpired:p.kill();p.wait(timeout=3)
   for n in reversed(created):subprocess.run(["ip","netns","del",n],check=False,capture_output=True,timeout=5)

if __name__=="__main__":main()
