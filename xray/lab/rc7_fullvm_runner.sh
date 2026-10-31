#!/usr/bin/env bash
# RC7 disposable full-system two-reboot test. Never run on a router.
set -euo pipefail
ROOT="$(pwd)"
: "$RUNNER_TEMP"
WORK="$RUNNER_TEMP/xray-v30-rc7-fullvm"
test ! -e "$WORK"
mkdir -p "$WORK"/initramfs/bin "$WORK"/initramfs/proc "$WORK"/initramfs/sys "$WORK"/initramfs/dev "$WORK"/initramfs/run "$WORK"/initramfs/mnt "$WORK"/rescue "$WORK"/active
for command_name in qemu-system-x86_64 busybox debugfs gcc cpio mkfs.ext4; do command -v "$command_name"; done
KERNEL="$(find /boot -maxdepth 1 -name 'vmlinuz-*-generic' -type f | sort -V | tail -1)"
test -s "$KERNEL" || { echo "RC7: NO_REAL_FULL_SYSTEM_KERNEL_HARD_NO_GO"; exit 77; }
echo "RC7: QEMU full-system kernel=$KERNEL"
# Ubuntu packaged kernel is root-readable only; copy inside disposable runner.
sudo cp "$KERNEL" "$WORK/guest-vmlinuz"
sudo chmod 644 "$WORK/guest-vmlinuz"
KERNEL="$WORK/guest-vmlinuz"
cp "$(command -v busybox)" "$WORK/initramfs/bin/busybox"
# Stock Ubuntu kernels may ship virtio/ext4 as .ko.zst rather than built-ins.
# Copy only kernel-provided dependency modules, in modprobe load order, into
# guest initramfs. This VM doesn't borrow any host kernel state at runtime.
mkdir -p "$WORK/initramfs/mods"
KVER="$(basename "$KERNEL" | sed 's/^vmlinuz-//')"
n=0
for modname in virtio_pci virtio_blk ext4; do
  while read -r opname module_path; do
    if [ "$opname" != insmod ]; then continue; fi
    n=$((n+1))
    out="$WORK/initramfs/mods/$(printf '%03d' "$n").ko"
    case "$module_path" in
      *.zst) zstd -dc "$module_path" > "$out" ;;
      *.xz) xz -dc "$module_path" > "$out" ;;
      *) cp "$module_path" "$out" ;;
    esac
  done < <(modprobe -S "$KVER" --show-depends "$modname")
done
echo "RC7: initramfs load-order kernel modules=$n"
gcc -O2 -static -Wall -Wextra "$ROOT/xray/lab/rc7_fullvm_cgroup_probe.c" -o "$WORK/initramfs/bin/rc7cgroup"
cp "$ROOT/xray/lab/rc7_fullvm_init" "$WORK/initramfs/init"
chmod 700 "$WORK/initramfs/init" "$WORK/initramfs/bin/rc7cgroup" "$WORK/initramfs/bin/busybox"
(
  cd "$WORK/initramfs"
  find . -print0 | cpio --null -o --format=newc 2>/dev/null | gzip -1 > "$WORK/initramfs.img.gz"
)
python3 - "$WORK/rescue" "$WORK/active" <<'PY'
from pathlib import Path
import sys,hashlib
from xray.lab.v30_review_rescue_bundle import file_set,SOURCES
rescue,active=map(Path,sys.argv[1:])
inputs=file_set()
lines=[]
for key in SOURCES:
    data=inputs["originals/"+key+".sh"]
    (rescue/(key+".sh")).write_bytes(data)
    lines.append(hashlib.sha256(data).hexdigest()+"  originals/"+key+".sh")
    (active/(key+".sh")).write_bytes(("CANDIDATE_NOT_ORIGINAL_"+key+"\n").encode())
(rescue/"SHA256SUMS").write_text("\n".join(lines)+"\n")
PY
for disk in rescue active entware-usb; do
  truncate -s 48M "$WORK/$disk.img"
  mkfs.ext4 -q -F "$WORK/$disk.img"
done
debugfs -w -R 'mkdir /originals' "$WORK/rescue.img" >/dev/null 2>&1
for name in S97 S98 S99 watchdog wifi_rules; do
  debugfs -w -R "write $WORK/rescue/$name.sh /originals/$name.sh" "$WORK/rescue.img" >/dev/null 2>&1
  debugfs -w -R "write $WORK/active/$name.sh /$name.sh" "$WORK/active.img" >/dev/null 2>&1
done
debugfs -w -R "write $WORK/rescue/SHA256SUMS /SHA256SUMS" "$WORK/rescue.img" >/dev/null 2>&1
echo "RC7: INDEPENDENT_VIRTUAL_DISK_FILES_PREPARED (not separate physical hardware)"
FIRST_LOG="$WORK/first-boot.log"
SECOND_LOG="$WORK/second-boot.log"
qemu-system-x86_64 -nodefaults -nographic -no-reboot -machine pc,accel=tcg -m 512 -smp 1 \
  -kernel "$KERNEL" -initrd "$WORK/initramfs.img.gz" -monitor none -display none \
  -drive "file=$WORK/rescue.img,format=raw,if=virtio,cache=writeback" \
  -drive "file=$WORK/active.img,format=raw,if=virtio,cache=writeback" \
  -drive "file=$WORK/entware-usb.img,format=raw,if=virtio,cache=writeback" \
  -append "console=ttyS0 rdinit=/init rc7_stage=first panic=-1" \
  -serial "file:$FIRST_LOG" >"$WORK/first-qemu-errors.log" 2>&1 &
FIRST_PID=$!
cleanup(){
  if kill -0 "$FIRST_PID" 2>/dev/null; then kill -KILL "$FIRST_PID" 2>/dev/null || true; wait "$FIRST_PID" 2>/dev/null || true; fi
}
trap cleanup EXIT
SUCCESS=0
for i in $(seq 1 180); do
  if [ -f "$FIRST_LOG" ] && grep -q 'RC7_VM: POWER_CUT_POINT_AFTER_FSYNC_TWO_FILES' "$FIRST_LOG"; then
    SUCCESS=1;break
  fi
  if ! kill -0 "$FIRST_PID" 2>/dev/null; then break; fi
  sleep 1
done
if [ "$SUCCESS" != 1 ]; then
  echo "RC7: FIRST_BOOT_FAILED_OR_TIMED_OUT" >&2
  tail -65 "$FIRST_LOG" || true
  echo "RC7: QEMU_STARTUP_DIAGNOSTIC:"
  cat "$WORK/first-qemu-errors.log" || true
  exit 1
fi
echo "RC7: QEMU_POWER_CUT_AFTER_EXACTLY_TWO_FSYNC_WRITES"
kill -KILL "$FIRST_PID" || true
wait "$FIRST_PID" 2>/dev/null || true
trap - EXIT
set +e
timeout --signal=KILL 170s qemu-system-x86_64 -nodefaults -nographic -no-reboot -machine pc,accel=tcg -m 512 -smp 1 \
  -kernel "$KERNEL" -initrd "$WORK/initramfs.img.gz" -monitor none -display none \
  -drive "file=$WORK/rescue.img,format=raw,if=virtio,cache=writeback" \
  -drive "file=$WORK/active.img,format=raw,if=virtio,cache=writeback" \
  -append "console=ttyS0 rdinit=/init rc7_stage=second panic=-1" \
  -serial "file:$SECOND_LOG" >"$WORK/second-qemu-errors.log" 2>&1
BOOT_EXIT=$?
set -e
if [ "$BOOT_EXIT" -ne 0 ]; then echo "RC7: SECOND_BOOT_EXIT=$BOOT_EXIT" >&2; fi
grep -q 'RC7_VM: PREVIOUS_TWO_FILES_AND_JOURNAL_SURVIVED_QEMU_SIGKILL' "$SECOND_LOG"
grep -q 'RC7_VM: EXACT_FIVE_RESCUE_ORIGINALS_VERIFIED' "$SECOND_LOG"
grep -q 'RC7_VM: REBOOT_FULL_RESTORE_5_OF_5_PASS' "$SECOND_LOG"
if grep -q 'RC7_VM: FAIL' "$SECOND_LOG"; then echo "RC7: GUEST_FAILURE" >&2;exit 1;fi
CGROUP="CGROUP1_GUEST_BLOCKED_NO_GO"
if grep -q 'RC7_GUEST: REAL_CGROUP_V1_FORK_EXEC_DRAIN_PASS' "$SECOND_LOG" &&
   grep -q 'RC7_GUEST: REAL_TCP_UDP_FD_INODE_OWNER_PASS' "$SECOND_LOG" &&
   grep -q 'RC7_GUEST: REAL_EIGHT_GUARDIAN_FLOCK_RACE_ROUND_1_ONE_WINNER' "$SECOND_LOG" &&
   grep -q 'RC7_GUEST: REAL_EIGHT_GUARDIAN_FLOCK_RACE_ROUND_2_ONE_WINNER' "$SECOND_LOG"; then
   CGROUP="REAL_CGROUP_V1_GUEST_FORK_EXEC_AND_8X2_FLOCK_PASS"
fi
printf '%s\n' "$CGROUP" >"$WORK/cgroup-disposition.txt"
echo "RC7: PASS_DISPOSABLE_QEMU_TWO_BOOT_POWERLOSS_RESCUE_5_OF_5"
echo "RC7: $CGROUP"
echo "RC7: HARD_NO_GO_PHYSICAL_KEENETIC_RUNTIME_CGROUP_BOOT_USB_TPROXY"
