"""RC30 independent-netns TCP/UDP echo, persistent connections across cutover."""
import socket,select,threading,time
DST=("10.77.0.3",19301)
TCP=b"RC30-TCP-"
UDP=b"RC30-UDP-"
tcp=socket.socket()
tcp.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
tcp.bind(DST);tcp.listen(16)
udp=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
udp.bind(DST)
print("RC30_BACKEND_INDEPENDENT_ORIGINAL_DEST_READY",flush=True)
received={"tcp":0,"udp":0}
def tcp_client(c):
 with c:
  c.settimeout(15)
  while True:
   try: payload=c.recv(256)
   except socket.timeout: break
   if not payload: break
   if not payload.startswith(TCP): raise RuntimeError("RC30_BAD_TCP_PAYLOAD")
   received["tcp"]+=1
   c.sendall(payload)
   print("RC30_BACKEND_TCP_ECHO",len(payload),flush=True)
threading.Thread(target=lambda:None,daemon=True).start()
until=time.monotonic()+68
while time.monotonic()<until:
 ready,_,_=select.select([tcp,udp],[],[],0.5)
 for s in ready:
  if s is tcp:
   conn,_=tcp.accept()
   threading.Thread(target=tcp_client,args=(conn,),daemon=True).start()
  else:
   data,peer=udp.recvfrom(256)
   if not data.startswith(UDP):raise RuntimeError("RC30_BAD_UDP_PAYLOAD")
   received["udp"]+=1
   udp.sendto(data,peer)
   print("RC30_BACKEND_UDP_ECHO",len(data),flush=True)
print("RC30_BACKEND_END_COUNTS",received,flush=True)
