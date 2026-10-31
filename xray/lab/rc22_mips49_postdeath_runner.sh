#!/usr/bin/env bash
set -euo pipefail
: "${RUNNER_TEMP:?DISPOSABLE_RUNNER_REQUIRED}"
[ "${GITHUB_ACTIONS:-}" = true ] || exit 2
W="$RUNNER_TEMP/rc22-mips49"; test ! -e "$W"
mkdir -p "$W/root" "$W/initramfs/proc" "$W/initramfs/sys" "$W/initramfs/dev"
curl -fL --retry 3 --max-time 120 -o "$W/kernel.deb" https://archive.debian.org/debian/pool/main/l/linux/linux-image-4.9.0-13-4kc-malta_4.9.228-1_mipsel.deb
printf '9a5dff9c498bf5736ca9f97cbb005b4b60bd139aa0f30f5bab9feca783907d9b  %s\n' "$W/kernel.deb" | sha256sum -c -
dpkg-deb -x "$W/kernel.deb" "$W/root"
K="$W/root/boot/vmlinux-4.9.0-13-4kc-malta"
printf '20f5380e02f2e40d4495fd61a854e5867f5ccdf95c8c1fd3d53fe27e8be1797f  %s\n' "$K" | sha256sum -c -
fetch(){
 local n="$1" p="$2" h="$3"
 curl -fL --retry 3 --max-time 120 -o "$W/$n.deb" "https://archive.debian.org/debian/pool/main/$p"
 printf '%s  %s\n' "$h" "$W/$n.deb" | sha256sum -c -
 test "$(dpkg-deb -f "$W/$n.deb" Architecture)" = mipsel
 dpkg-deb -x "$W/$n.deb" "$W/initramfs"
}
fetch iptables 'i/iptables/iptables_1.6.0+snapshot20161117-6_mipsel.deb' b0bd6d7e4bc7da38672b223cb428315309979a19e008aedafb17253315178b67
fetch iproute2 'i/iproute2/iproute2_4.9.0-1+deb9u1_mipsel.deb' c0b0886583db81db0a517e0945be52d23dcc3ee5fe8ea068bfdaa80cb639213d
fetch busybox 'b/busybox/busybox-static_1.22.0-19+b3_mipsel.deb' 0c7e287104914e654a2555e9900302180ff54d1ef17e9faf585529e6eadac8e0
fetch libc6 'g/glibc/libc6_2.24-11+deb9u4_mipsel.deb' 5515fb37ad178bb61b5ce53e0d36860d865779174352403ee7ed20976777f129
fetch libip4tc0 'i/iptables/libip4tc0_1.6.0+snapshot20161117-6_mipsel.deb' f2182182b5a4834c7cb81cbedb8666731c0de8368cf53b9a908d58dca9369db8
fetch libip6tc0 'i/iptables/libip6tc0_1.6.0+snapshot20161117-6_mipsel.deb' 80b61d515779bc62fbbac799d5d5fbe102f97f860d4ec11a42ca3dc4f3c3f820
fetch libxtables12 'i/iptables/libxtables12_1.6.0+snapshot20161117-6_mipsel.deb' d820b1df1df638a5d2682a827f06c7e4032546da786db2f714bf70b1dad0937b
python3 -m xray.lab.rc20_mips49_tproxy_module_pack --root "$W/root" --dest "$W/initramfs/mod" | tee "$W/module-order.log"
mkdir -p "$W/initramfs/lab"
mkdir -p "$W/initramfs/bin" "$W/initramfs/etc"
curl -fL --retry 3 --max-time 120 -o "$W/xray.zip" https://github.com/XTLS/Xray-core/releases/download/v26.2.6/Xray-linux-mips32le.zip
printf '1590b2bcefe64fb0604f29c8c75219bfbe8f63daa3bc8e3956edfa6da97c5869  %s\n' "$W/xray.zip" | sha256sum -c -
unzip -j "$W/xray.zip" xray -d "$W/initramfs/bin"
printf '3d2588c5ef770a6a7e1bfdd5db511130fb3acd79eb91bfcb108753b3e1dda1f6  %s\n' "$W/initramfs/bin/xray" | sha256sum -c -
chmod 755 "$W/initramfs/bin/xray"
mipsel-linux-gnu-gcc -static -O2 -Wall -Wextra -o "$W/initramfs/bin/rc9capwrap" xray/lab/rc9_guest_capwrap.c
# Original host-facing destination stays 10.0.2.15:19191 (TPROXY).
# Deliberately separate the loopback-only backend TCP/UDP bind port 19292:
# Xray's transparent UDP response socket otherwise competes with an in-guest
# backend bound to *:19191 and fails with fake: socket bind: EADDRINUSE.
# This tests real transparent ingress + controlled guest-only redirect,
# NOT production-style original-destination preservation after outbound.
cat >"$W/initramfs/etc/xray.json" <<'JSON'
{
  "log":{"loglevel":"debug"},
  "inbounds":[{
    "tag":"lab-tproxy","listen":"0.0.0.0","port":12345,
    "protocol":"dokodemo-door",
    "settings":{"network":"tcp,udp","followRedirect":true},
    "streamSettings":{"sockopt":{"tproxy":"tproxy"}}
  }],
  "outbounds":[
    {"tag":"local-only","protocol":"freedom","settings":{"redirect":"127.0.0.1:19292"}},
    {"tag":"blocked","protocol":"blackhole","settings":{}}
  ],
  "routing":{"rules":[
    {"type":"field","inboundTag":["lab-tproxy"],"outboundTag":"local-only"},
    {"type":"field","port":"0-65535","outboundTag":"blocked"}
  ]}
}
JSON
chmod 644 "$W/initramfs/etc/xray.json"
mipsel-linux-gnu-gcc -static -O2 -Wall -Wextra -o "$W/initramfs/init" xray/lab/rc21_mips49_guest_xray_init.c
mipsel-linux-gnu-gcc -static -O2 -Wall -Wextra -DPORT=19292 -o "$W/initramfs/lab/echo" xray/lab/rc19_mips49_tcpudp_echo.c
mipsel-linux-gnu-gcc -static -O2 -Wall -Wextra -DPORT=19191 -o "$W/initramfs/lab/echo-orig" xray/lab/rc19_mips49_tcpudp_echo.c
cp xray/lab/rc22_mips49_postdeath_packet.sh "$W/initramfs/lab/xray-packet.sh"
chmod 755 "$W/initramfs/lab/echo" "$W/initramfs/lab/echo-orig" "$W/initramfs/lab/xray-packet.sh"
mkdir -p "$W/initramfs/lab"
chmod 755 "$W/initramfs/init"
test -f "$W/initramfs/lib/mipsel-linux-gnu/ld-2.24.so"
test -f "$W/initramfs/lib/mipsel-linux-gnu/libc-2.24.so"
test -f "$W/initramfs/sbin/iptables"; test -f "$W/initramfs/bin/ip"
(cd "$W/initramfs"; find . -print0 | cpio --null -o --format=newc 2>/dev/null | gzip -1 >"$W/guest.cpio.gz")
set +e
timeout --signal=KILL 165s qemu-system-mipsel -M malta -cpu 4KEc -m 512 -smp 1 -nographic -no-reboot -nodefaults -netdev user,id=isolated,restrict=on,hostfwd=tcp:127.0.0.1:19191-:19191,hostfwd=udp:127.0.0.1:19191-:19191 -device pcnet,netdev=isolated,romfile= -monitor none -kernel "$K" -initrd "$W/guest.cpio.gz" -append "console=ttyS0 rdinit=/init panic=1" -serial "file:$W/serial.log" >"$W/qemu-errors.log" 2>&1 &
qemu_pid=$!
set -e
ready=0
for n in $(seq 1 260); do
 if grep -Fq 'RC22_GUEST: XRAY_READY_SEND_BASELINE' "$W/serial.log" 2>/dev/null; then ready=1; break; fi
 if ! kill -0 "$qemu_pid" 2>/dev/null; then break; fi
 sleep 0.25
done
if [ "$ready" != 1 ]; then
 echo 'RC19_HARD_NO_GO_GUEST_NIC_NOT_READY'
 cat "$W/serial.log" "$W/qemu-errors.log" 2>/dev/null || true
 wait "$qemu_pid" || true
 exit 1
fi
set +e
python3 - <<'PY'
import pathlib,socket,time
serial=pathlib.Path(__import__("os").environ["RUNNER_TEMP"])/"rc22-mips49"/"serial.log"
tcp=b'RC19-TCP-PAYLOAD-20261031';udp=b'RC19-UDP-PAYLOAD-20261031'
def wait_marker(marker,seconds=30):
 for _ in range(int(seconds*5)):
  if marker in serial.read_text(errors="replace") if serial.exists() else False:
   return
  time.sleep(.2)
 raise RuntimeError("RC22_HARD_NO_GO_MARKER_MISSING "+marker)
wait_marker("RC22_GUEST: XRAY_READY_SEND_BASELINE",25)
with socket.create_connection(("127.0.0.1",19191),timeout=10) as s:
 s.sendall(tcp)
 got=s.recv(512)
 assert got==tcp,("RC22_HARD_NO_GO_BASELINE_TCP",got)
 print("RC22_HOST: BASELINE_REAL_TCP_XRAY_ECHO",len(got),flush=True)
with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
 s.settimeout(.7)
 for _ in range(3):
  s.sendto(udp,("127.0.0.1",19191))
  try:
   data,_=s.recvfrom(512)
   if data==udp:
    print("RC22_HOST: BASELINE_UDP_HOST_RETURN_OBSERVED",len(data),flush=True)
    break
  except socket.timeout:
   pass
 else:
  print("RC22_HOST: UDP_HOST_RETURN_UNPROVEN_RESTRICT_ON",flush=True)
wait_marker("RC22_GUEST: POSTDEATH_SENTINEL_READY_SEND_PROBES",30)
print("RC22_HOST: REAL_POSTDEATH_TCP_UDP_PROBES_BEGIN",flush=True)
try:
 with socket.create_connection(("127.0.0.1",19191),timeout=2) as s:
  s.settimeout(2)
  s.sendall(tcp)
  data=s.recv(512)
  print("RC22_HOST: POSTDEATH_TCP_RETURN_BYTES",len(data),flush=True)
except (OSError,TimeoutError) as e:
 print("RC22_HOST: POSTDEATH_TCP_NO_RETURN",type(e).__name__,flush=True)
with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
 s.settimeout(.7)
 for _ in range(4):
  s.sendto(udp,("127.0.0.1",19191))
  try:
   data,_=s.recvfrom(512)
   print("RC22_HOST: POSTDEATH_UDP_RETURN_BYTES",len(data),flush=True)
   break
  except socket.timeout:
   pass
print("RC22_HOST: POSTDEATH_PROBES_SENT_NO_RETURN_CLAIM",flush=True)
PY
client_status=$?
set -e
if [ "$client_status" -ne 0 ]; then
 echo "RC19_HARD_NO_GO_HOST_CLIENT_PACKET_CHECK_FAILED"
 tail -n 130 "$W/serial.log" || true
 tail -n 40 "$W/qemu-errors.log" || true
 exit "$client_status"
fi
set +e
wait "$qemu_pid"
status=$?
set -e

grep -E 'RC18_GUEST:|RC13_GUEST:|RC19_GUEST:|RC21_GUEST:|RC22_GUEST:|RC9_CAP:' "$W/serial.log" || true
if grep -Fq 'RC22_GUEST: OBSERVED_DIRECT_FALLBACK_AFTER_XRAY_DEATH_HARD_NO_GO' "$W/serial.log"; then
  echo 'RC22: HARD_NO_GO_DIRECT_BYPASS_AFTER_XRAY_DEATH_OBSERVED'
  exit 3
fi
test "$status" -eq 0 || { echo 'RC22: HARD_NO_GO_GUEST_EXIT_STATUS'; exit 2; }
grep -Fq 'RC22_GUEST: REAL_XRAY_TCP_UDP_BASELINE_BACKEND_PASS' "$W/serial.log"
grep -Fq 'RC22_GUEST: XRAY_LISTENERS_GONE_AFTER_PARENT_OWNED_SIGNAL' "$W/serial.log"
grep -Fq 'RC22_GUEST: POSTDEATH_NO_SENTINEL_RECEIPT_BOUNDED_LAB_ONLY' "$W/serial.log"
echo 'RC22: BOUNDED_NO_SENTINEL_RECEIPT_AFTER_XRAY_DEATH_ONLY_NOT_VENDOR_NOREGRESS'
echo 'RC22: HARD_NO_GO_HOST_UDP_RETURN_LEGACY_FENCING_VENDOR_HARDWARE'
