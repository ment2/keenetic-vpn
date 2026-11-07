#!/usr/bin/env python3
"""RC44 only: native IP_TRANSPARENT TCP/UDP packets in disposable netns."""
import os,select,socket,struct,sys,time
DST=("198.18.44.10",19444)
def serve():
 ss=[]
 for protocol in ("tcp","udp"):
  sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM if protocol=="tcp" else socket.SOCK_DGRAM)
  sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
  sock.setsockopt(socket.SOL_IP,getattr(socket,"IP_TRANSPARENT",19),1)
  sock.bind(("0.0.0.0",12345))
  if protocol=="tcp":sock.listen(3)
  ss.append((sock,protocol))
  try:ck=struct.unpack("=Q",sock.getsockopt(socket.SOL_SOCKET,57,8))[0]
  except OSError:ck=-1
  print("RC44_REAL_TRANSPARENT_LISTENER",protocol,"inode",os.fstat(sock.fileno()).st_ino,"cookie",ck,flush=True)
 deadline=time.monotonic()+40
 while time.monotonic()<deadline:
  ready,_,_=select.select([x[0] for x in ss],[],[],.25)
  for sock in ready:
   protocol=dict(ss)[sock]
   if protocol=="udp":
    msg,peer=sock.recvfrom(512)
    assert msg.startswith(b"RC44-")
    print("RC44_REAL_TPROXY_UDP_PACKET",msg.decode(),flush=True)
   else:
    conn,peer=sock.accept()
    with conn:
     conn.settimeout(2);msg=conn.recv(512);assert msg.startswith(b"RC44-")
     print("RC44_REAL_TPROXY_TCP_PACKET",msg.decode(),flush=True)
     conn.sendall(msg)
 for sock,_ in ss:sock.close()
def probe(phase):
 assert phase in ("PRE","REPAIR","ROLLBACK")
 with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
  s.bind(("10.44.0.2",0))
  msg=("RC44-"+phase+"-UDP").encode();s.sendto(msg,DST)
  print("RC44_CLIENT_UDP_SENT",phase,flush=True)
 with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
  s.bind(("10.44.0.2",0));s.settimeout(2)
  try:
   s.connect(DST)
   msg=("RC44-"+phase+"-TCP").encode();s.sendall(msg)
   ans=s.recv(512)
   if phase!="REPAIR" or ans!=msg:raise RuntimeError("UNSAFE_DIRECT_OR_ECHO_MISMATCH")
   print("RC44_CLIENT_REPAIR_TCP_EXACT_ECHO",flush=True)
  except (OSError,socket.timeout) as e:
   if phase=="REPAIR":raise
   print("RC44_CLIENT_"+phase+"_TCP_BLOCKED",type(e).__name__,flush=True)
if __name__=="__main__":
 if len(sys.argv)!=2:raise SystemExit("serve|pre|repair|rollback")
 if sys.argv[1]=="serve":serve()
 else:probe(sys.argv[1].upper())
