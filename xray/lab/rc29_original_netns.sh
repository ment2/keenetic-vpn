#!/usr/bin/env bash
set -euo pipefail
test "$GITHUB_ACTIONS" = true
W="$1"; K="$2"
test "$(ip -o link show | wc -l)" -eq 1 || { echo RC29_HARD_NO_GO_NONEMPTY_RUNNER_NETNS;exit 10; }
test -z "$(ip -4 route show default)" || { echo RC29_HARD_NO_GO_DEFAULT_ROUTE;exit 10; }
ip link set lo up
test -c /dev/net/tun || { echo RC29_HARD_NO_GO_TUN_UNAVAILABLE;exit 10; }
ip link add br29 type bridge
ip addr add 10.77.0.1/24 dev br29
ip link set br29 up
ip tuntap add dev tap29 mode tap
ip link set tap29 master br29
ip link set tap29 up
unshare --net -- sleep 95 &
backend_ns=$!
trap 'kill "$backend_ns" 2>/dev/null || true' EXIT
ip link add v29h type veth peer name v29b
ip link set v29h master br29
ip link set v29h up
ip link set v29b netns "$backend_ns"
nsenter -t "$backend_ns" -n -- ip link set lo up
nsenter -t "$backend_ns" -n -- ip addr add 10.77.0.3/24 dev v29b
nsenter -t "$backend_ns" -n -- ip link set v29b up
nsenter -t "$backend_ns" -n -- python3 -u xray/lab/rc29_original_backend.py >"$W/backend.log" 2>&1 &
backend=$!
for n in $(seq 1 60); do
 if grep -Fq 'RC29_BACKEND: SEPARATE_NETNS_BOUND_ORIGINAL_10_77_0_3' "$W/backend.log" 2>/dev/null; then break;fi
 sleep 0.1
done
grep -Fq 'RC29_BACKEND: SEPARATE_NETNS_BOUND_ORIGINAL_10_77_0_3' "$W/backend.log"
# Force only host-originated 10.77.0.3/32 traffic through guest 10.77.0.2.
# Guest Xray's outbound to backend is still connected /24, no redirect.
ip route add 10.77.0.3/32 via 10.77.0.2 dev br29
echo RC29_NETNS_SEPARATE_BACKEND_AND_ROUTED_ORIGINAL_DST_NO_DEFAULT
timeout --signal=KILL 90s qemu-system-mipsel -M malta -cpu 4KEc -m 512 -smp 1 -nographic -no-reboot -nodefaults \
 -netdev user,id=restricted,restrict=on -device pcnet,netdev=restricted,romfile= \
 -netdev tap,id=independent,ifname=tap29,script=no,downscript=no -device pcnet,netdev=independent,romfile= \
 -monitor none -kernel "$K" -initrd "$W/guest.cpio.gz" -append "console=ttyS0 rdinit=/init panic=1" \
 -serial "file:$W/serial.log" >"$W/qemu-errors.log" 2>&1 &
qemu=$!
trap 'kill "$qemu" "$backend" "$backend_ns" 2>/dev/null || true' EXIT
ready=0
for n in $(seq 1 200); do
 if grep -Fq RC29_GUEST_REAL_XRAY_CAP_NET_RAW_NNP_READY "$W/serial.log" 2>/dev/null;then ready=1;break;fi
 if ! kill -0 "$qemu" 2>/dev/null;then break;fi
 sleep 0.2
done
if [ "$ready" -ne 1 ];then
 echo RC29_HARD_NO_GO_XRAY_GUEST_NOT_READY
 tail -n 70 "$W/serial.log" || true; cat "$W/qemu-errors.log" || true;exit 11
fi
set +e
python3 - <<'PY'
import socket
dst=("10.77.0.3",19301)
tcp=b"RC29-TCP-ORIGINAL-DEST";udp=b"RC29-UDP-ORIGINAL-DEST"
with socket.create_connection(dst,timeout=7) as s:
 s.settimeout(6);s.sendall(tcp)
 got=s.recv(256)
 assert got==tcp,("RC29_HARD_NO_GO_ORIGINAL_DEST_TCP_RETURN",got)
 print("RC29_HOST: REAL_MIPS_XRAY_TCP_ORIGINAL_DEST_RESPONSE",len(got),flush=True)
with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
 s.settimeout(1.4)
 for n in range(3):
  s.sendto(udp,dst)
  try:
   got,peer=s.recvfrom(256)
   assert got==udp and peer==dst,("RC29_HARD_NO_GO_ORIGINAL_DEST_UDP_REPLY",got,peer)
   print("RC29_HOST: REAL_MIPS_XRAY_UDP_ORIGINAL_DEST_RESPONSE",len(got),flush=True)
   break
  except socket.timeout:
   print("RC29_HOST: UDP_ORIGINAL_RETURN_TIMEOUT",n+1,flush=True)
 else:
  raise RuntimeError("RC29_HARD_NO_GO_ORIGINAL_DEST_UDP_RETURN_UNPROVEN")
PY
client=$?
set -e
set +e
wait "$qemu"
status=$?
wait "$backend"
backend_status=$?
set -e
grep -E 'RC29_GUEST|RC13_GUEST|RC18_GUEST' "$W/serial.log" || true
cat "$W/backend.log" || true
if [ "$client" -ne 0 ] || [ "$status" -ne 0 ] || [ "$backend_status" -ne 0 ];then
 echo "RC29_HARD_NO_GO_ORIGINAL_DEST_PATH client=$client guest=$status backend=$backend_status";exit 12
fi
grep -Fq RC29_GUEST_REAL_XRAY_ORIGINAL_DEST_TPROXY_COUNTERS_POSITIVE "$W/serial.log"
grep -Fq RC29_BACKEND:\ ORIGINAL_DEST_TCP_ECHO_EXACT "$W/backend.log"
grep -Fq RC29_BACKEND:\ ORIGINAL_DEST_UDP_ECHO_EXACT "$W/backend.log"
echo RC29_PASS_REAL_MIPS49_XRAY_TCP_UDP_ORIGINAL_DEST_INDEPENDENT_BACKEND
echo RC29_HARD_NO_GO_SLIRP_HOSTFWD_LEGACY_ROOT_FENCING_PHYSICAL_RESCUE
