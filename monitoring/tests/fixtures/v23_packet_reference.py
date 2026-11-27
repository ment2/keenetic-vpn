#!/usr/bin/env python3
"""Independent real-kernel reference kill-switch lab; disposable GitHub runner only.

Three isolated namespaces; no physical interface, no WAN, no production rules.
Tests forwarding and router-originated TCP, UDP, DNS UDP and DNS TCP. This is
not an assertion that the Keenetic's vendor chains implement this reference.
"""
import os
import pathlib
import subprocess
import sys
import tempfile
import time
import uuid

SERVER = r'''
import socket,selectors,sys,struct
sel=selectors.DefaultSelector()
for typ,port in ((socket.SOCK_STREAM,18080),(socket.SOCK_DGRAM,18081),(socket.SOCK_DGRAM,53),(socket.SOCK_STREAM,53)):
 s=socket.socket(socket.AF_INET,typ);s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);s.bind(("198.19.0.2",port))
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
CLIENT = r'''
import socket,sys,struct
phase,origin,kind,token=sys.argv[1:]
dns=kind.startswith("dns")
tcp=kind in ("tcp","dns_tcp")
port=53 if dns else (18080 if tcp else 18081)
if dns:
 labels=[token.encode(),b"fixture",b"invalid"]
 payload=b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"+b"".join(bytes([len(x)])+x for x in labels)+b"\x00\x00\x01\x00\x01"
 if tcp:payload=struct.pack("!H",len(payload))+payload
else:payload=token.encode()
s=socket.socket(socket.AF_INET,socket.SOCK_STREAM if tcp else socket.SOCK_DGRAM)
s.settimeout(.75)
try:
 s.connect(("198.19.0.2",port));s.sendall(payload);b=s.recv(4096)
 if phase!="allow" or b!=payload:raise SystemExit(2)
except (TimeoutError,ConnectionError,OSError):
 if phase=="allow":raise
finally:s.close()
print(payload.hex(),flush=True)
'''
def main():
 if os.environ.get("GITHUB_ACTIONS")!="true" or os.geteuid()!=0:
  raise SystemExit("disposable CI root required")
 suffix=uuid.uuid4().hex[:6]
 client,router,sink=["v23"+x+suffix for x in "crs"]
 created=[]
 def run(*a, **kw):return subprocess.run(a,check=True,text=True,capture_output=True,timeout=10,**kw).stdout
 def ip(n,*a):return run("ip","-n",n,*a)
 def ns(n,*a):return run("ip","netns","exec",n,*a)
 with tempfile.TemporaryDirectory(prefix="v23-packet-fixture-") as tmp:
  log=pathlib.Path(tmp)/"sentinel.log"
  server=None
  try:
   for n in (client,router,sink):
    run("ip","netns","add",n);created.append(n);ip(n,"link","set","lo","up")
   # veth devices created inside disposable namespaces, not attached to host.
   ip(client,"link","add","c0","type","veth","peer","name","r0","netns",router)
   ip(router,"link","add","r1","type","veth","peer","name","s0","netns",sink)
   for n,dev,addr in ((client,"c0","198.18.0.2/24"),(router,"r0","198.18.0.1/24"),(router,"r1","198.19.0.1/24"),(sink,"s0","198.19.0.2/24")):
    ip(n,"addr","add",addr,"dev",dev);ip(n,"link","set",dev,"up")
   ip(client,"route","add","198.19.0.0/24","via","198.18.0.1")
   ip(sink,"route","add","198.18.0.0/24","via","198.19.0.1")
   ns(router,"sysctl","-qw","net.ipv4.ip_forward=1")
   for chain in ("FORWARD","OUTPUT"):
    ns(router,"iptables","-P",chain,"ACCEPT")
   with log.open("w") as f:
    server=subprocess.Popen(["ip","netns","exec",sink,sys.executable,"-u","-c",SERVER],stdout=f,stderr=f)
   for _ in range(50):
    if "READY" in log.read_text():break
    if server.poll() is not None:raise RuntimeError("sentinel failed")
    time.sleep(.1)
   else:raise RuntimeError("sentinel not ready")
   kinds=("tcp","udp","dns_udp","dns_tcp")
   positive=[];negative=[]
   for n,label in ((client,"forward"),(router,"output")):
    for kind in kinds:
     token=uuid.uuid4().hex
     positive.append(ns(n,sys.executable,"-c",CLIENT,"allow",label,kind,token).strip())
   text=log.read_text()
   assert all(x in text for x in positive) and len(positive)==8
   print("POSITIVE_RECEIPTS",len(positive),flush=True)
   # Reference kill-switch: deny every packet leaving isolated WAN device.
   for chain in ("FORWARD","OUTPUT"):
    ns(router,"iptables","-I",chain,"1","-o","r1","-j","DROP")
   for n,label in ((client,"forward"),(router,"output")):
    for kind in kinds:
     token=uuid.uuid4().hex
     negative.append(ns(n,sys.executable,"-c",CLIENT,"deny",label,kind,token).strip())
   text=log.read_text()
   assert not any(x in text for x in negative) and len(negative)==8
   for chain in ("FORWARD","OUTPUT"):
    counters=ns(router,"iptables","-L",chain,"-xvn")
    matches=[line.split() for line in counters.splitlines() if "DROP" in line and "r1" in line]
    assert len(matches)==1 and int(matches[0][0])>=4
    print("DROP_COUNTER",chain,matches[0][0],flush=True)
   print("NEGATIVE_RECEIPTS",0,"ATTEMPTS",len(negative),"REFERENCE_IPV4_ONLY",flush=True)
  finally:
   if server is not None:
    server.terminate()
    try:server.wait(timeout=3)
    except subprocess.TimeoutExpired:server.kill();server.wait(timeout=3)
   for n in reversed(created):subprocess.run(["ip","netns","del",n],check=False,capture_output=True,timeout=5)

if __name__=="__main__":main()
