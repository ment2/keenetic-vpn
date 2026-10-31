#!/usr/bin/env bash
set -euo pipefail
test "$GITHUB_ACTIONS" = true
W="$1"; K="$2"
test "$(ip -o link show | wc -l)" -eq 1 || { echo RC30_HARD_NO_GO_NONEMPTY_RUNNER_NETNS;exit 10; }
test -z "$(ip -4 route show default)" || { echo RC30_HARD_NO_GO_DEFAULT_ROUTE;exit 10; }
ip link set lo up
test -c /dev/net/tun || { echo RC30_HARD_NO_GO_TUN_UNAVAILABLE;exit 10; }
ip link add br30 type bridge
ip addr add 10.77.0.1/24 dev br30
ip link set br30 up
ip tuntap add dev tap30 mode tap
ip link set tap30 master br30
ip link set tap30 up
unshare --net -- sleep 95 &
backend_ns=$!
trap 'kill "$backend_ns" 2>/dev/null || true' EXIT
ip link add v30h type veth peer name v30b
ip link set v30h master br30
ip link set v30h up
ip link set v30b netns "$backend_ns"
nsenter -t "$backend_ns" -n -- ip link set lo up
nsenter -t "$backend_ns" -n -- ip addr add 10.77.0.3/24 dev v30b
nsenter -t "$backend_ns" -n -- ip link set v30b up
nsenter -t "$backend_ns" -n -- python3 -u xray/lab/rc30_first_tproxy_backend.py >"$W/backend.log" 2>&1 &
backend=$!
for n in $(seq 1 60); do
 if grep -Fq 'RC30_BACKEND_INDEPENDENT_ORIGINAL_DEST_READY' "$W/backend.log" 2>/dev/null; then break;fi
 sleep 0.1
done
grep -Fq 'RC30_BACKEND: SEPARATE_NETNS_BOUND_ORIGINAL_10_77_0_3' "$W/backend.log"
# Force only host-originated 10.77.0.3/32 traffic through guest 10.77.0.2.
# Guest Xray's outbound to backend is still connected /24, no redirect.
ip route add 10.77.0.3/32 via 10.77.0.2 dev br30
echo RC30_NETNS_SEPARATE_BACKEND_AND_ROUTED_ORIGINAL_DST_NO_DEFAULT
timeout --signal=KILL 90s qemu-system-mipsel -M malta -cpu 4KEc -m 512 -smp 1 -nographic -no-reboot -nodefaults \
 -netdev user,id=restricted,restrict=on -device pcnet,netdev=restricted,romfile= \
 -netdev tap,id=independent,ifname=tap30,script=no,downscript=no -device pcnet,netdev=independent,romfile= \
 -monitor none -kernel "$K" -initrd "$W/guest.cpio.gz" -append "console=ttyS0 rdinit=/init panic=1" \
 -serial "file:$W/serial.log" >"$W/qemu-errors.log" 2>&1 &
qemu=$!
trap 'kill "$qemu" "$backend" "$backend_ns" 2>/dev/null || true' EXIT
ready=0
for n in $(seq 1 200); do
 if grep -Fq RC30_GUEST_OLD_AND_CANDIDATE_XRAY_TCP_UDP_READY "$W/serial.log" 2>/dev/null;then ready=1;break;fi
 if ! kill -0 "$qemu" 2>/dev/null;then break;fi
 sleep 0.2
done
if [ "$ready" -ne 1 ];then
 echo RC30_HARD_NO_GO_XRAY_GUEST_NOT_READY
 tail -n 70 "$W/serial.log" || true; cat "$W/qemu-errors.log" || true;exit 11
fi
set +e
python3 - <<'PY'
import os,socket,time
from pathlib import Path
serial=Path(os.environ["RUNNER_TEMP"])/"rc30-first-tproxy-handover"/"serial.log"
dst=("10.77.0.3",19301)
def marker(value,seconds=21):
 for _ in range(int(seconds*10)):
  if serial.exists() and value in serial.read_text(errors="replace"):
   print("RC30_HOST: GUEST_STAGE",value,flush=True);return
  time.sleep(.1)
 raise RuntimeError("RC30_HARD_NO_GO_STAGE_MISSING "+value)
def tcp_conn(port):
 s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
 s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
 s.bind(("10.77.0.1",port))
 s.settimeout(5)
 s.connect(dst)
 return s
def tcpecho(s,label):
 data=("RC30-TCP-"+label).encode()
 s.sendall(data)
 reply=s.recv(256)
 assert reply==data,("RC30_HARD_NO_GO_TCP",label,reply)
 print("RC30_HOST: TCP_EXACT",label,len(reply),flush=True)
def udpecho(s,label):
 data=("RC30-UDP-"+label).encode()
 for trial in range(3):
  s.sendto(data,dst)
  try:
   reply,peer=s.recvfrom(256)
   assert reply==data and peer==dst,("RC30_HARD_NO_GO_UDP",label,reply,peer)
   print("RC30_HOST: UDP_EXACT",label,len(reply),flush=True)
   return
  except socket.timeout:
   print("RC30_HOST: UDP_RETRY",label,trial+1,flush=True)
 raise RuntimeError("RC30_HARD_NO_GO_UDP_"+label)
def udp_sock(port):
 s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
 s.bind(("10.77.0.1",port))
 s.settimeout(1.1)
 return s
marker("RC30_GUEST_OLD_AND_CANDIDATE_XRAY_TCP_UDP_READY")
with tcp_conn(21111) as old_tcp, udp_sock(21112) as old_udp:
 tcpecho(old_tcp,"OLD_BEFORE")
 udpecho(old_udp,"OLD_BEFORE")
 marker("RC30_GUEST_NEW_ONLY_TUPLE_PINNED_CUTOVER_READY")
 tcpecho(old_tcp,"OLD_DURING")
 udpecho(old_udp,"OLD_DURING")
 with tcp_conn(21114) as new_tcp:
  tcpecho(new_tcp,"NEW_DURING")
 with udp_sock(21113) as new_udp:
  udpecho(new_udp,"NEW_DURING")
 marker("RC30_GUEST_CUTOVER_RULES_REMOVED_ROLLBACK_READY")
 tcpecho(old_tcp,"OLD_AFTER_ROLLBACK")
 udpecho(old_udp,"OLD_AFTER_ROLLBACK")
 with tcp_conn(21115) as restored_tcp:
  tcpecho(restored_tcp,"NEW_AFTER_ROLLBACK")
 with udp_sock(21116) as restored_udp:
  udpecho(restored_udp,"NEW_AFTER_ROLLBACK")
 print("RC30_HOST: PASS_KNOWN_OLD_TUPLE_TCP_UDP_ACROSS_CUTOVER_AND_ROLLBACK",flush=True)
PY
client=$?
set -e
set +e
wait "$qemu"
status=$?
kill "$backend" 2>/dev/null
wait "$backend" 2>/dev/null
set -e
grep -E 'RC30_GUEST|RC13_GUEST|RC18_GUEST' "$W/serial.log" || true
cat "$W/backend.log" || true
if [ "$client" -ne 0 ] || [ "$status" -ne 0 ];then
 echo "RC30_HARD_NO_GO_FIRST_CUTOVER client=$client guest=$status"; exit 12
fi
grep -Fq RC30_GUEST_TWO_XRAY_PID_STARTTICKS_UNCHANGED_GENERATION_CAS_SYNTHETIC "$W/serial.log"
grep -Fq RC30_GUEST_CUTOVER_RULES_REMOVED_ROLLBACK_READY "$W/serial.log"
grep -Fq 'RC30_BACKEND_TCP_ECHO' "$W/backend.log"
grep -Fq 'RC30_BACKEND_UDP_ECHO' "$W/backend.log"
echo RC30_PASS_KNOWN_TUPLE_TPROXY_TCP_UDP_INITIAL_CUTOVER_ONLY
echo RC30_HARD_NO_GO_DYNAMIC_UDP_5TUPLE_CAS_PRIVILEGED_LEGACY_FENCING_PHYSICAL
