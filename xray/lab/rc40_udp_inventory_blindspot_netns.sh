#!/usr/bin/env bash
set -euo pipefail
test "$GITHUB_ACTIONS" = true
W="$1"; K="$2"
test "$(ip -o link show | wc -l)" -eq 1 || { echo RC40_HARD_NO_GO_NONEMPTY_RUNNER_NETNS;exit 10; }
test -z "$(ip -4 route show default)" || { echo RC40_HARD_NO_GO_DEFAULT_ROUTE;exit 10; }
ip link set lo up
test -c /dev/net/tun || { echo RC40_HARD_NO_GO_TUN_UNAVAILABLE;exit 10; }
ip link add br30 type bridge
ip addr add 10.77.0.1/24 dev br30
ip link set br30 up
ip tuntap add dev tap30 mode tap
ip link set tap30 master br30
ip link set tap30 up
unshare --net -- sleep 95 &
backend_ns=$!
trap 'kill "$backend_ns" 2>/dev/null || true' EXIT
ip link add v33h type veth peer name v33b
ip link set v33h master br30
ip link set v33h up
ip link set v33b netns "$backend_ns"
nsenter -t "$backend_ns" -n -- ip link set lo up
nsenter -t "$backend_ns" -n -- ip addr add 10.77.0.3/24 dev v33b
nsenter -t "$backend_ns" -n -- ip link set v33b up
nsenter -t "$backend_ns" -n -- python3 -u xray/lab/rc30_first_tproxy_backend.py >"$W/backend.log" 2>&1 &
backend=$!
for n in $(seq 1 60); do
 if grep -Fq 'RC30_BACKEND_INDEPENDENT_ORIGINAL_DEST_READY' "$W/backend.log" 2>/dev/null; then break;fi
 sleep 0.1
done
grep -Fq 'RC30_BACKEND_INDEPENDENT_ORIGINAL_DEST_READY' "$W/backend.log"
# Force only host-originated 10.77.0.3/32 traffic through guest 10.77.0.2.
# Guest Xray's outbound to backend is still connected /24, no redirect.
ip route add 10.77.0.3/32 via 10.77.0.2 dev br30
echo RC40_NETNS_SEPARATE_BACKEND_AND_ROUTED_ORIGINAL_DST_NO_DEFAULT
timeout --signal=KILL 90s qemu-system-mipsel -M malta -cpu 4KEc -m 512 -smp 1 -nographic -no-reboot -nodefaults \
 -netdev user,id=restricted,restrict=on -device pcnet,netdev=restricted,romfile= \
 -netdev tap,id=independent,ifname=tap30,script=no,downscript=no -device pcnet,netdev=independent,romfile= \
 -monitor none -kernel "$K" -initrd "$W/guest.cpio.gz" -append "console=ttyS0 rdinit=/init panic=1" \
 -serial "file:$W/serial.log" >"$W/qemu-errors.log" 2>&1 &
qemu=$!
trap 'kill "$qemu" "$backend" "$backend_ns" 2>/dev/null || true' EXIT
ready=0
for n in $(seq 1 200); do
 if grep -Fq RC40_GUEST_READY_TO_PRIME_IDLE_UDP "$W/serial.log" 2>/dev/null;then ready=1;break;fi
 if ! kill -0 "$qemu" 2>/dev/null;then break;fi
 sleep 0.2
done
if [ "$ready" -ne 1 ];then
 echo RC40_HARD_NO_GO_XRAY_GUEST_NOT_READY
 tail -n 70 "$W/serial.log" || true; cat "$W/qemu-errors.log" || true;exit 11
fi
set +e
python3 - <<'PY'
import os,socket,time,sys
from pathlib import Path
serial=Path(os.environ["RUNNER_TEMP"])/"rc40-udp-inventory-blindspot"/"serial.log"
dst=("10.77.0.3",19301)
def stage(key,seconds=23):
 for _ in range(int(seconds*10)):
  if serial.exists() and key in serial.read_text(errors="replace"):
   print("RC40_HOST: GUEST_STAGE",key,flush=True)
   return
  time.sleep(.1)
 raise RuntimeError("RC40_HARD_NO_GO_STAGE_MISSING "+key)
def udp_sock():
 s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
 s.bind(("10.77.0.1",0));s.settimeout(1.2)
 return s
def ident(s):
 sock_inode=os.fstat(s.fileno()).st_ino
 # Linux SO_COOKIE: kernel-assigned stable 64-bit socket identity
 cookie=int.from_bytes(s.getsockopt(socket.SOL_SOCKET,57,8),sys.byteorder)
 assert cookie>0 and sock_inode>0,("RC40_HARD_NO_GO_SOCKET_INODE_COOKIE",sock_inode,cookie)
 return (s.getsockname()[0],s.getsockname()[1],sock_inode,cookie)
def echo(s,label):
 payload=("RC40-UDP-"+label).encode()
 for attempt in range(3):
  s.sendto(payload,dst)
  try:
   reply,peer=s.recvfrom(256)
   assert reply==payload and peer==dst,("RC40_HARD_NO_GO_BAD_PACKET",label,reply,peer)
   print("RC40_HOST: UDP_EXACT",label,len(reply),flush=True)
   return
  except socket.timeout:
   print("RC40_HOST: UDP_ECHO_RETRY",label,attempt,flush=True)
 raise RuntimeError("RC40_HARD_NO_GO_NO_UDP_ECHO:"+label)
with udp_sock() as old_a,udp_sock() as unseen_b:
 a=ident(old_a); b=ident(unseen_b)
 assert a[1]!=b[1] and a[2]!=b[2] and a[3]!=b[3]
 print("RC40_HOST: TWO_DISTINCT_LIVE_SOCKET_INODES_COOKIES",a,b,flush=True)
 stage("RC40_GUEST_READY_TO_PRIME_IDLE_UDP")
 echo(old_a,"A_BEFORE_EXPIRY")
 print("RC40_HOST: B_BOUND_BUT_NEVER_SENT",b[1],flush=True)
 stage("RC40_GUEST_REAL_OLD_UDP_CONNTRACK_ENTRY_WITNESSED")
 stage("RC40_GUEST_SNAPSHOT_READY_OLD_A_LIVE_IN_XRAY_B_NEVER_DISPATCHED",seconds=28)
 assert ident(old_a)==a and ident(unseen_b)==b
 print("RC40_HOST: AT_SNAPSHOT_A_SILENT_AND_B_UNSENT_BOTH_SOCKETS_UNCHANGED",flush=True)
 echo(old_a,"A_AFTER_CONNTRACK_EXPIRY")
 echo(unseen_b,"B_FIRST_EVER_PACKET")
 assert ident(old_a)==a and ident(unseen_b)==b
 stage("RC40_GUEST_LOG_NEW_DISPATCH_ONCE")
 blob=serial.read_text(errors="replace")
 import re
 m=re.search(r"RC40_GUEST_LOG_NEW_DISPATCH_ONCE sourceport=(\d+)",blob)
 assert m and int(m.group(1))==b[1],("RC40_HARD_NO_GO_GUEST_NEW_OWNER_PORT_MISMATCH",m.group(1) if m else None,b[1])
 old=re.search(r"RC40_GUEST_LOG_OLD_REUSED_ONCE sourceport=(\d+)",blob)
 assert old and int(old.group(1))==a[1],("RC40_HARD_NO_GO_GUEST_OLD_OWNER_PORT_MISMATCH",a[1])
 print("RC40_HOST: REAL_MIPS49_XRAY_LOG_DISPATCH_OLD_REUSED_B_NEW_SOURCE_PORTS_MATCH",flush=True)
 print("RC40_HOST: PASS_TWO_SOCKET_KERNEL_OBSERVER_CANNOT_RECONSTRUCT_XRAY_OWNER",flush=True)

PY
client=$?
set -e
set +e
wait "$qemu"
status=$?
kill "$backend" 2>/dev/null || true
wait "$backend" 2>/dev/null || true
set -e
grep -E 'RC40_GUEST|RC13_GUEST|RC18_GUEST' "$W/serial.log" || true
cat "$W/backend.log" || true
if [ "$client" -ne 0 ] || [ "$status" -ne 0 ];then echo "RC40_HARD_NO_GO_CLIENT_OR_GUEST_FAIL client=$client guest=$status";exit 12;fi
grep -Fq RC40_PASS_TWO_REAL_MIPS49_UDP_SOCKET_STATES_KERNEL_SNAPSHOT_AMBIGUOUS "$W/serial.log"
grep -Fq RC40_GUEST_PROCESS_STARTTICKS_BOOT_UNCHANGED_NO_ROUTE_CUTOVER "$W/serial.log"
grep -Fq RC40_HARD_NO_GO_NO_ATOMIC_KERNEL_FREEZE_DURABLE_CAS_OR_PRIVILEGED_ROOT_FENCE "$W/serial.log"
echo RC40_REAL_MIPS49_NEGATIVE_COMPLETE_KERNEL_UDP_INVENTORY_WITNESS_CONFIRMED
echo RC40_HARD_NO_GO_PRODUCTION_NO_COMPLETE_XRAY_OWNER_MAP_OR_ATOMIC_FREEZE
