"""Only disposable RC42 real UDP endpoints, not Xray session ownership."""
import os,socket,struct,sys,time
def who(s):
 v=open("/proc/self/stat").read(); f=v[v.rfind(") ")+2:].split()
 return (os.getpid(),f[19],os.fstat(s.fileno()).st_ino,struct.unpack("=Q",s.getsockopt(socket.SOL_SOCKET,57,8))[0])
def client(cmd,events):
 s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.bind(("10.42.0.2",0));s.settimeout(1)
 original=who(s)
 assert original[2]>0 and original[3]>0
 with open(cmd,encoding="ascii") as commands,open(events,"w",buffering=1) as output:
  output.write(f"RC42_CLIENT_READY pid={original[0]} ticks={original[1]} inode={original[2]} cookie={original[3]} port={s.getsockname()[1]}\n")
  for line in commands:
   phase=line.strip()
   if phase=="STOP":
    output.write("RC42_CLIENT_STOPPED\n");break
   if phase not in ("BEFORE","FROZEN","AFTER"):raise RuntimeError("BAD_PHASE")
   msg=("RC42-"+phase).encode("ascii")
   s.sendto(msg,("10.42.0.1",19542))
   try:data,addr=s.recvfrom(512)
   except socket.timeout:
    if phase!="FROZEN":raise RuntimeError("RC42_EXPECTED_ECHO_MISSING_"+phase)
    output.write("RC42_CLIENT_FROZEN_PACKET_TIMED_OUT_IN_REAL_KERNEL\n");continue
   if phase=="FROZEN":raise RuntimeError("RC42_KERNEL_DROP_BYPASSED")
   if data!=msg or addr!=("10.42.0.1",19542):raise RuntimeError("RC42_ECHO_MISMATCH")
   if who(s)!=original:raise RuntimeError("RC42_SOCKET_IDENTITY_CHANGED")
   output.write(f"RC42_CLIENT_{phase}_EXACT_ECHO bytes={len(data)}\n")
 s.close()
def server():
 s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.bind(("10.42.0.1",19542));s.settimeout(.3)
 p,t,ino,cookie=who(s)
 print(f"RC42_SERVER_READY pid={p} ticks={t} inode={ino} cookie={cookie}",flush=True)
 end=time.monotonic()+60
 while time.monotonic()<end:
  try:data,peer=s.recvfrom(512)
  except socket.timeout:continue
  if not data.startswith(b"RC42-"):raise RuntimeError("RC42_NON_FIXTURE_PACKET")
  print("RC42_SERVER_RECEIVED "+data.decode("ascii"),flush=True)
  s.sendto(data,peer)
 s.close()
if __name__=="__main__":
 if sys.argv[1:]==["server"]:server()
 elif len(sys.argv)==4 and sys.argv[1]=="client":client(sys.argv[2],sys.argv[3])
 else:raise SystemExit("RC42 invalid endpoint arguments")
