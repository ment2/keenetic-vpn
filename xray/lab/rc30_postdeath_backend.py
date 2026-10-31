#!/usr/bin/env python3
"""Separate Linux network namespace TCP/UDP echo, only exact test payloads."""
import socket,select,time,sys
DST=("10.77.0.3",19301)
T=b"RC29-TCP-ORIGINAL-DEST"
U=b"RC29-UDP-ORIGINAL-DEST"
a=socket.socket();b=socket.socket(type=socket.SOCK_DGRAM)
a.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
a.bind(DST);a.listen(4);b.bind(DST)
print("RC29_BACKEND: SEPARATE_NETNS_BOUND_ORIGINAL_10_77_0_3",flush=True)
seen=set()
deadline=time.monotonic()+42
while time.monotonic()<deadline and len(seen)<2:
 ready,_,_=select.select([a,b],[],[],1)
 for s in ready:
  if s is a:
   conn,peer=a.accept();conn.settimeout(4)
   data=conn.recv(256)
   if data!=T:raise AssertionError(("WRONG_ORIGINAL_TCP",data))
   conn.sendall(data);conn.close()
   print("RC29_BACKEND: ORIGINAL_DEST_TCP_ECHO_EXACT",peer,len(data),flush=True)
   seen.add("tcp")
  else:
   data,peer=b.recvfrom(256)
   if data!=U:raise AssertionError(("WRONG_ORIGINAL_UDP",data))
   b.sendto(data,peer)
   print("RC29_BACKEND: ORIGINAL_DEST_UDP_ECHO_EXACT",peer,len(data),flush=True)
   seen.add("udp")
print("RC29_BACKEND: COMPLETE_PROTOCOLS",sorted(seen),flush=True)
if seen != {"tcp","udp"}:
 sys.exit(3)
# The independent original destination remains LIVE after Xray's death.
# Any post-death canary reaching this backend is positive bypass evidence.
deadline=time.monotonic()+19
while time.monotonic()<deadline:
 ready,_,_=select.select([a,b],[],[],0.4)
 for s in ready:
  if s is a:
   conn,peer=a.accept();conn.settimeout(2)
   data=conn.recv(256);conn.close()
   print("RC30_BACKEND: HARD_NO_GO_POSTDEATH_TCP_REACHED_REAL_BACKEND",peer,repr(data),flush=True)
   sys.exit(4)
  else:
   data,peer=b.recvfrom(256)
   print("RC30_BACKEND: HARD_NO_GO_POSTDEATH_UDP_REACHED_REAL_BACKEND",peer,repr(data),flush=True)
   sys.exit(5)
print("RC30_BACKEND: NO_TCP_UDP_POSTDEATH_CANARY_DELIVERED_IN_BOUNDED_WINDOW",flush=True)
sys.exit(0)
