#!/usr/bin/env bash
# RC11 MIPS32LE Linux4.9 full-system QEMU only, no external networking/router.
set -euo pipefail
ROOT="$(pwd)"
: "$RUNNER_TEMP"
WORK="$RUNNER_TEMP/rc11-mips49-fullsystem"
test ! -e "$WORK"
mkdir -p "$WORK"/{kernel-root,initramfs/bin,initramfs/etc,initramfs/proc,initramfs/sys,initramfs/run,initramfs/tmp}
curl -fL --retry 3 --max-time 120 -o "$WORK/kernel.deb" https://archive.debian.org/debian/pool/main/l/linux/linux-image-4.9.0-13-4kc-malta_4.9.228-1_mipsel.deb
curl -fL --retry 3 --max-time 120 -o "$WORK/xray.zip" https://github.com/XTLS/Xray-core/releases/download/v26.2.6/Xray-linux-mips32le.zip
printf '9a5dff9c498bf5736ca9f97cbb005b4b60bd139aa0f30f5bab9feca783907d9b  %s\n' "$WORK/kernel.deb" | sha256sum -c -
printf '1590b2bcefe64fb0604f29c8c75219bfbe8f63daa3bc8e3956edfa6da97c5869  %s\n' "$WORK/xray.zip" | sha256sum -c -
dpkg-deb -x "$WORK/kernel.deb" "$WORK/kernel-root"
KERNEL="$WORK/kernel-root/boot/vmlinux-4.9.0-13-4kc-malta"
printf '20f5380e02f2e40d4495fd61a854e5867f5ccdf95c8c1fd3d53fe27e8be1797f  %s\n' "$KERNEL" | sha256sum -c -
unzip -j "$WORK/xray.zip" xray -d "$WORK/initramfs/bin"
printf '3d2588c5ef770a6a7e1bfdd5db511130fb3acd79eb91bfcb108753b3e1dda1f6  %s\n' "$WORK/initramfs/bin/xray" | sha256sum -c -
readelf -h "$KERNEL" | grep -q 'little endian'
readelf -h "$WORK/initramfs/bin/xray" | grep -q 'little endian'
mipsel-linux-gnu-gcc -static -O2 -Wall -Wextra -o "$WORK/initramfs/init" "$ROOT/xray/lab/rc11_mips49_guest_init.c"
mipsel-linux-gnu-gcc -static -O2 -Wall -Wextra -o "$WORK/initramfs/bin/rc9capwrap" "$ROOT/xray/lab/rc9_guest_capwrap.c"
mipsel-linux-gnu-gcc -static -O2 -Wall -Wextra -o "$WORK/initramfs/bin/rc9socket" "$ROOT/xray/lab/rc10_guest_socket_cap_probe.c"
mipsel-linux-gnu-gcc -static -O2 -Wall -Wextra -o "$WORK/initramfs/bin/rc10cas" "$ROOT/xray/lab/rc10_guest_guardian_generation_cas.c"
mipsel-linux-gnu-gcc -static -O2 -Wall -Wextra -o "$WORK/initramfs/bin/rc7cgroup" "$ROOT/xray/lab/rc7_fullvm_cgroup_probe.c"
mipsel-linux-gnu-gcc -static -O2 -Wall -Wextra -o "$WORK/initramfs/bin/rc8privdrop" "$ROOT/xray/lab/rc8_guest_privdrop.c"
cat > "$WORK/initramfs/etc/xray.json" <<'JSON'
{
 "log":{"loglevel":"warning"},
 "inbounds":[{"tag":"lab-no-route","listen":"127.0.0.1","port":12345,
 "protocol":"dokodemo-door","settings":{"network":"tcp,udp","followRedirect":true},
 "streamSettings":{"sockopt":{"tproxy":"tproxy"}}}],
 "outbounds":[{"tag":"no-external","protocol":"blackhole","settings":{}}],
 "routing":{"rules":[{"type":"field","inboundTag":["lab-no-route"],"outboundTag":"no-external"}]}
}
JSON
chmod 755 "$WORK/initramfs/init" "$WORK/initramfs/bin/"*
chmod 644 "$WORK/initramfs/etc/xray.json"
(
 cd "$WORK/initramfs"
 find . -print0 | cpio --null -o --format=newc 2>/dev/null | gzip -1 > "$WORK/guest-initramfs.cpio.gz"
)
echo "RC11: REAL_ARCHIVE_KERNEL_AND_MIPS32LE_XRAY_SHA256_VERIFIED"
set +e
timeout --signal=KILL 150s qemu-system-mipsel -M malta -cpu 4KEc -m 512 -smp 1 \
 -nographic -no-reboot -nodefaults -net none -monitor none \
 -kernel "$KERNEL" -initrd "$WORK/guest-initramfs.cpio.gz" \
 -append "console=ttyS0 rdinit=/init panic=1" \
 -serial "file:$WORK/guest-serial.log" > "$WORK/qemu-errors.log" 2>&1
STATUS=$?
set -e
echo "RC11: QEMU_EXIT_STATUS=$STATUS"
if [ "$STATUS" -ne 0 ]; then
 echo "RC11: REAL_MIPS49_BOOT_NOT_VERIFIED_HARD_NO_GO" >&2
 tail -n 80 "$WORK/guest-serial.log" || true
 cat "$WORK/qemu-errors.log" || true
 exit 1
fi
for phrase in \
 'RC11_MIPS49: REAL_FULLSYSTEM_KERNEL_BOOT' \
 'RC10_SOCKET: VERIFIED_NO_NEW_PRIVS_SURVIVED_EXEC_ON_KERNEL49' \
 'RC11_MIPS49: IN_GUEST_UNPRIVILEGED_TRANSPARENT_SOCKETS_DENIED' \
 'RC11_MIPS49: IN_GUEST_ONLY_CAP_NET_RAW_TCP_UDP_IP_TRANSPARENT_PASS' \
 'RC7_GUEST: PRIVILEGED_CGROUP_ESCAPE_SUCCEEDED_HARD_NO_GO' \
 'RC8_GUEST: EIGHT_REAL_UNPRIV_FORK_SETSID_EXEC_ESCAPE_DENIALS_PASS' \
 'RC8_GUEST: GUARDIAN_DENIES_RESTART_UNKNOWN_REPARENTED_DESCENDANT' \
 'RC8_GUEST: UNPRIVILEGED_ORPHAN_DRAINED_NO_RESTART_BEFORE_ABSENCE' \
 'RC11_MIPS49: PRIVILEGED_ESCAPE_NATIVELY_OBSERVED_IN_MIPS_CGROUP_V1_HARD_NO_GO' \
 'RC11_MIPS49: EIGHT_UNPRIVILEGED_DESCENDANTS_AND_UNKNOWN_ORPHAN_NO_RESTART_PASS' \
 'RC10_CAS: REAL_LINUX49_8X3_GENERATION_FLOCK_PREPARED_CRASH_RECOVERY_PASS' \
 'RC11_MIPS49: REAL_MIPS_XRAY_26_2_6_UID65534_CAP_NET_RAW_ONLY_INBOUND_PASS' \
 'RC11_MIPS49: PARENT_OWNED_MIPS_XRAY_NO_STALE_PID_SIGNAL_LISTENER_DRAIN_PASS' \
 'RC11_MIPS49: REAL_MIPS49_FULL_TPROXY_PACKETS_NOT_TESTED' \
 'RC11_MIPS49: PHYSICAL_KEENETIC_NDM5_PRODUCTION_HARD_NO_GO'; do
 grep -Fq "$phrase" "$WORK/guest-serial.log" || {
  echo "RC11: MISSING_REQUIRED_GUEST_PROOF $phrase" >&2
  tail -n 90 "$WORK/guest-serial.log" || true
  exit 1
 }
done
if grep -q 'RC11_MIPS49: HARD_NO_GO' "$WORK/guest-serial.log"; then
 echo "RC11: guest safety abort" >&2
 exit 1
fi
echo "RC11: PASS_REAL_MIPS32LE_LINUX49_FULLSYSTEM_XRAY_CAP_NET_RAW_CAS_GUEST_ONLY"
echo "RC11: HARD_NO_GO_MIPS_KERNEL49_TPROXY_FULL_PACKET_PATH_UNTESTED"
echo "RC11: HARD_NO_GO_PHYSICAL_VENDOR_NDM5_MIPS_UNKNOWN"
