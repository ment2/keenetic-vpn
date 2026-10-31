#!/usr/bin/env bash
set -euo pipefail
: "${RUNNER_TEMP:?DISPOSABLE_RUNNER_REQUIRED}"
[ "${GITHUB_ACTIONS:-}" = true ] || exit 2
W="$RUNNER_TEMP/rc33-dynamic-udp-tproxy-handover"; test ! -e "$W"
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
# Candidate gets an *independent* fixed config, same narrowed capabilities.
sed 's|/etc/xray.json|/etc/xray-candidate.json|g' xray/lab/rc9_guest_capwrap.c >"$W/rc30_capwrap.c"
mipsel-linux-gnu-gcc -static -O2 -Wall -Wextra -o "$W/initramfs/bin/rc30capwrap" "$W/rc30_capwrap.c"
# Both processes route real original TCP/UDP destination WITHOUT redirect.
# The old config has NO API and owns the legacy listener 12345.
cat >"$W/initramfs/etc/xray.json" <<'JSON'
{
  "log":{"loglevel":"debug"},
  "inbounds":[{"tag":"legacy-tproxy","listen":"0.0.0.0","port":12345,
    "protocol":"dokodemo-door","settings":{"network":"tcp,udp","followRedirect":true},
    "streamSettings":{"sockopt":{"tproxy":"tproxy"}}}],
  "outbounds":[{"tag":"backend","protocol":"freedom","settings":{}},
               {"tag":"blocked","protocol":"blackhole","settings":{}}],
  "routing":{"rules":[{"type":"field","inboundTag":["legacy-tproxy"],"outboundTag":"backend"},
                       {"type":"field","port":"0-65535","outboundTag":"blocked"}]}
}
JSON
cat >"$W/initramfs/etc/xray-candidate.json" <<'JSON'
{
  "log":{"loglevel":"debug"},
  "api":{"tag":"lab-api","services":["HandlerService","RoutingService"]},
  "inbounds":[
    {"tag":"lab-api","listen":"127.0.0.1","port":21808,
     "protocol":"dokodemo-door","settings":{"address":"127.0.0.1"}},
    {"tag":"candidate-tproxy","listen":"0.0.0.0","port":22345,
     "protocol":"dokodemo-door","settings":{"network":"tcp,udp","followRedirect":true},
     "streamSettings":{"sockopt":{"tproxy":"tproxy"}}}
  ],
  "outbounds":[{"tag":"backend","protocol":"freedom","settings":{}},
               {"tag":"blocked","protocol":"blackhole","settings":{}}],
  "routing":{"rules":[{"type":"field","inboundTag":["lab-api"],"outboundTag":"lab-api"},
                       {"type":"field","inboundTag":["candidate-tproxy"],"outboundTag":"backend"},
                       {"type":"field","port":"0-65535","outboundTag":"blocked"}]}
}
JSON
chmod 644 "$W/initramfs/etc/xray.json" "$W/initramfs/etc/xray-candidate.json"
mipsel-linux-gnu-gcc -static -O2 -Wall -Wextra -o "$W/initramfs/init" xray/lab/rc29_original_init.c
mipsel-linux-gnu-gcc -static -O2 -Wall -Wextra -DPORT=19292 -o "$W/initramfs/lab/echo" xray/lab/rc19_mips49_tcpudp_echo.c
mipsel-linux-gnu-gcc -static -O2 -Wall -Wextra -o "$W/initramfs/lab/rc33-observer" xray/lab/rc33_udp_flow_observer.c
chmod 755 "$W/initramfs/lab/rc33-observer"
cp xray/lab/rc33_dynamic_udp_first_tproxy_guest.sh "$W/initramfs/lab/xray-packet.sh"
chmod 755 "$W/initramfs/lab/echo" "$W/initramfs/lab/xray-packet.sh"
mkdir -p "$W/initramfs/lab"
chmod 755 "$W/initramfs/init"
test -f "$W/initramfs/lib/mipsel-linux-gnu/ld-2.24.so"
test -f "$W/initramfs/lib/mipsel-linux-gnu/libc-2.24.so"
test -f "$W/initramfs/sbin/iptables"; test -f "$W/initramfs/bin/ip"
(cd "$W/initramfs"; find . -print0 | cpio --null -o --format=newc 2>/dev/null | gzip -1 >"$W/guest.cpio.gz")
# Original destination backend resides in a separate host Linux netns.
# No default route or host networking. Existing SLIRP restrict=on remains.
sudo --preserve-env=RUNNER_TEMP,GITHUB_ACTIONS unshare --net -- bash xray/lab/rc33_dynamic_udp_first_tproxy_netns.sh "$W" "$K"
