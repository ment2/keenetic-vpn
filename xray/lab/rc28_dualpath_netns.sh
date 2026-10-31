#!/usr/bin/env bash
set -euo pipefail
test "$GITHUB_ACTIONS" = true
W="$1"; K="$2"
test -n "$W" && test -n "$K" && test -n "$RUNNER_TEMP"
test "$(ip -o link show | wc -l)" -eq 1 || { echo RC28_HARD_NO_GO_NONEMPTY_NETNS; exit 11; }
test -z "$(ip -4 route show default)" || { echo RC28_HARD_NO_GO_DEFAULT_ROUTE_PRESENT; exit 11; }
ip link set lo up
test -c /dev/net/tun || { echo RC28_HARD_NO_GO_TUN_DEVICE_MISSING; exit 12; }
ip tuntap add dev tap28 mode tap
ip addr add 10.77.0.1/24 dev tap28
ip link set tap28 up
echo RC28_NETNS_PRIVATE_TAP_ONLY_NO_DEFAULT
timeout --signal=KILL 90s qemu-system-mipsel -M malta -cpu 4KEc -m 512 -smp 1 -nographic -no-reboot -nodefaults \
 -netdev user,id=restricted,restrict=on,hostfwd=tcp:127.0.0.1:19301-:19301,hostfwd=udp:127.0.0.1:19301-:19301 \
 -device pcnet,netdev=restricted,romfile= -netdev tap,id=independent,ifname=tap28,script=no,downscript=no \
 -device pcnet,netdev=independent,romfile= -monitor none -kernel "$K" -initrd "$W/guest.cpio.gz" \
 -append "console=ttyS0 rdinit=/init panic=1" -serial "file:$W/serial.log" >"$W/qemu-errors.log" 2>&1 &
pid=$!
trap 'kill "$pid" 2>/dev/null || true' EXIT
ready=0
for n in $(seq 1 180); do
 if grep -Fq 'RC23_GUEST: TCP_UDP_SOCKET_READY' "$W/serial.log" 2>/dev/null; then ready=1; break; fi
 if ! kill -0 "$pid" 2>/dev/null; then break; fi
 sleep 0.2
done
if [ "$ready" -ne 1 ]; then
 echo RC28_HARD_NO_GO_GUEST_NOT_READY
 tail -n 100 "$W/serial.log" || true
 cat "$W/qemu-errors.log" || true
 exit 13
fi
python3 - <<'PY'
import socket
T=b'RC23-TCP-HOSTFWD-BASELINE'
U=b'RC23-UDP-HOSTFWD-BASELINE'
dst=('10.77.0.2',19301)
with socket.create_connection(dst,timeout=7) as s:
 s.settimeout(7);s.sendall(T)
 assert s.recv(256)==T,'TAP_TCP_CONTROL_BAD'
print('RC28_HOST: PRIVATE_TAP_TCP_RETURN_EXACT',flush=True)
with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
 s.bind(('10.77.0.1',0));s.settimeout(1.25)
 for n in range(3):
  s.sendto(U,dst)
  try:
   received,peer=s.recvfrom(256)
   assert received==U and peer==dst,('TAP_UDP_WRONG_REPLY',received,peer)
   print('RC28_HOST: PRIVATE_TAP_BIDIRECTIONAL_UDP_EXACT_RECEIVED',len(received),flush=True)
   break
  except socket.timeout:
   print('RC28_HOST: PRIVATE_TAP_UDP_TIMEOUT',n+1,flush=True)
 else:
  raise RuntimeError('RC28_HARD_NO_GO_PRIVATE_TAP_UDP_RETURN_NOT_OBSERVED')
with socket.create_connection(('127.0.0.1',19301),timeout=7) as s:
 s.settimeout(7);s.sendall(T)
 assert s.recv(256)==T,'SLIRP_TCP_CONTROL_BAD'
print('RC28_HOST: SLIRP_TCP_RETURN_EXACT',flush=True)
with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
 s.settimeout(.75)
 for n in range(3):
  s.sendto(U,('127.0.0.1',19301))
  try:
   received,_=s.recvfrom(256)
   assert received==U,'SLIRP_UDP_WRONG_REPLY'
   print('RC28_HOST: SLIRP_UDP_RETURN_EXACT',len(received),flush=True)
   break
  except socket.timeout:
   print('RC28_HOST: SLIRP_UDP_RETURN_TIMEOUT',n+1,flush=True)
 else:
  print('RC28_HOST: SLIRP_UDP_RETURN_UNPROVEN_DESPITE_TAP_CONTROL',flush=True)
PY
set +e
wait "$pid"
status=$?
set -e
grep -E 'RC28_GUEST|RC23_GUEST' "$W/serial.log" || true
if [ "$status" -ne 0 ]; then echo "RC28_HARD_NO_GO_GUEST_EXIT_$status"; exit 14; fi
grep -Fq 'RC28_GUEST: DUAL_PCNET_NO_DEFAULT_ROUTE' "$W/serial.log"
grep -Fq 'RC23_GUEST: UDP_SENDTO_EXACT' "$W/serial.log"
echo RC28_PASS_PRIVATE_TAP_UDP_ONLY_WITH_SLIRP_RESTRICT_ON
echo RC28_HARD_NO_GO_SLIRP_ORIGINAL_DESTINATION_REAL_XRAY_PRIVILEGED_FENCE_PHYSICAL_RESCUE
