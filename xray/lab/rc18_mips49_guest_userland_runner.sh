#!/usr/bin/env bash
set -euo pipefail
: "${RUNNER_TEMP:?DISPOSABLE_RUNNER_REQUIRED}"
[ "${GITHUB_ACTIONS:-}" = true ] || exit 2
W="$RUNNER_TEMP/rc18-mips49"; test ! -e "$W"
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
python3 -m xray.lab.rc13_mips49_module_dependency_pack --root "$W/root" --dest "$W/initramfs/mod" | tee "$W/module-order.log"
mipsel-linux-gnu-gcc -static -O2 -Wall -Wextra -o "$W/initramfs/init" xray/lab/rc18_mips49_guest_userland_init.c
chmod 755 "$W/initramfs/init"
test -f "$W/initramfs/lib/mipsel-linux-gnu/ld-2.24.so"
test -f "$W/initramfs/lib/mipsel-linux-gnu/libc-2.24.so"
test -f "$W/initramfs/sbin/iptables"; test -f "$W/initramfs/bin/ip"
(cd "$W/initramfs"; find . -print0 | cpio --null -o --format=newc 2>/dev/null | gzip -1 >"$W/guest.cpio.gz")
set +e
timeout --signal=KILL 130s qemu-system-mipsel -M malta -cpu 4KEc -m 512 -smp 1 -nographic -no-reboot -nodefaults -net none -monitor none -kernel "$K" -initrd "$W/guest.cpio.gz" -append "console=ttyS0 rdinit=/init panic=1" -serial "file:$W/serial.log" >"$W/qemu-errors.log" 2>&1
status=$?
set -e
grep -E 'RC18_GUEST:|RC13_GUEST:' "$W/serial.log" || true
test "$status" -eq 0
for marker in 'RC18_GUEST: EXEC_SUCCESS MIPS_IPROUTE2_VERSION' 'RC18_GUEST: EXEC_SUCCESS MIPS_IPTABLES_VERSION' 'RC18_GUEST: EXEC_SUCCESS MIPS_IPTABLES_MANGLE_READONLY' 'RC13_GUEST: MIPS49_USERLAND_EXECUTABLE_LIBC_XTABLES_CLOSURE_SUCCESS' 'RC13_GUEST: HARD_NO_GO_TCP_UDP_PACKET_PATH_NOT_EXECUTED'; do
 grep -Fq "$marker" "$W/serial.log" || { echo "RC18_HARD_NO_GO_MISSING_MARKER $marker"; exit 1; }
done
echo 'RC18: SUCCESS_EXECUTABLE_MIPS49_USERLAND_CLOSURE_NO_NIC'
echo 'RC18: HARD_NO_GO_ACTUAL_TCP_UDP_PACKET_PATH_AND_PHYSICAL_HARDWARE'
