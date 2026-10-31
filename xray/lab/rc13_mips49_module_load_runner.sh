#!/usr/bin/env bash
# QEMU Malta MIPS32LE only. All network interfaces disabled.
set -euo pipefail
: "${RUNNER_TEMP:?DISPOSABLE_GITHUB_RUNNER_REQUIRED}"
ROOT="$(pwd)"
W="$RUNNER_TEMP/rc13-mips49-moduleload"
test ! -e "$W"
mkdir -p "$W"/{root,initramfs/proc,initramfs/sys}
curl -fL --retry 3 --max-time 120 -o "$W/kernel.deb" \
  https://archive.debian.org/debian/pool/main/l/linux/linux-image-4.9.0-13-4kc-malta_4.9.228-1_mipsel.deb
printf '9a5dff9c498bf5736ca9f97cbb005b4b60bd139aa0f30f5bab9feca783907d9b  %s\n' "$W/kernel.deb" | sha256sum -c -
dpkg-deb -x "$W/kernel.deb" "$W/root"
K="$W/root/boot/vmlinux-4.9.0-13-4kc-malta"
printf '20f5380e02f2e40d4495fd61a854e5867f5ccdf95c8c1fd3d53fe27e8be1797f  %s\n' "$K" | sha256sum -c -
python3 -m xray.lab.rc13_mips49_module_dependency_pack --root "$W/root" --dest "$W/initramfs/mod" |
  tee "$W/module-dependency-order.log"
mipsel-linux-gnu-gcc -static -O2 -Wall -Wextra \
  -o "$W/initramfs/init" "$ROOT/xray/lab/rc13_mips49_guest_module_init.c"
chmod 755 "$W/initramfs/init"
(
  cd "$W/initramfs"
  find . -print0 | cpio --null -o --format=newc 2>/dev/null | gzip -1 > "$W/guest-initramfs.cpio.gz"
)
set +e
timeout --signal=KILL 125s qemu-system-mipsel -M malta -cpu 4KEc -m 512 -smp 1 \
 -nographic -no-reboot -nodefaults -net none -monitor none \
 -kernel "$K" -initrd "$W/guest-initramfs.cpio.gz" \
 -append "console=ttyS0 rdinit=/init panic=1" \
 -serial "file:$W/serial.log" > "$W/qemu-errors.log" 2>&1
status=$?
set -e
echo "RC13: QEMU_EXIT_STATUS=$status"
grep -E 'RC13_GUEST: (MODULE_LOAD|REAL_MIPS49|NO_GUEST|HARD_NO_GO)' "$W/serial.log" || true
# Module-load failure stays a real discovery blocker. Do not claim runtime pass.
if [ "$status" -ne 0 ] || ! grep -Fq 'RC13_GUEST: REAL_MIPS49_NETFILTER_XTABLES_TPROXY_MODULES_LOADED' "$W/serial.log"; then
  echo "RC13: HARD_NO_GO_MIPS_KERNEL49_TPROXY_MODULE_LOAD_NOT_VERIFIED"
  exit 1
fi
grep -Fq 'RC13_GUEST: NO_GUEST_NIC_IPTABLES_RULES_FWMARK_OR_POLICY_ROUTE' "$W/serial.log"
grep -Fq 'RC13_GUEST: HARD_NO_GO_TCP_UDP_PACKET_PATH_NOT_EXECUTED' "$W/serial.log"
echo "RC13: PASS_REAL_MIPS49_KERNEL_MODULE_LOAD_DISPOSABLE_GUEST_ONLY"
echo "RC13: HARD_NO_GO_REAL_MIPS_TCP_UDP_PACKET_PATH_AND_PHYSICAL_HARDWARE"
