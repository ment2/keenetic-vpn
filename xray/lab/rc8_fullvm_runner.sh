#!/usr/bin/env bash
# RC7 disposable full-system two-reboot test. Never run on a router.
set -euo pipefail
ROOT="$(pwd)"
: "$RUNNER_TEMP"
SCENARIO="${RC8_SCENARIO:-baseline}"
case "$SCENARIO" in baseline|journal-corrupt|rescue-corrupt) ;; *) echo "RC8: bad scenario" >&2; exit 2;; esac
WORK="$RUNNER_TEMP/xray-v30-rc8-fullvm-$SCENARIO"
test ! -e "$WORK"
mkdir -p "$WORK"/initramfs/bin "$WORK"/initramfs/proc "$WORK"/initramfs/sys "$WORK"/initramfs/dev "$WORK"/initramfs/run "$WORK"/initramfs/mnt "$WORK"/rescue "$WORK"/active
for command_name in qemu-system-x86_64 busybox debugfs gcc cpio mkfs.ext4; do command -v "$command_name"; done
KERNEL="$(find /boot -maxdepth 1 -name 'vmlinuz-*-generic' -type f | sort -V | tail -1)"
test -s "$KERNEL" || { echo "RC8: NO_REAL_FULL_SYSTEM_KERNEL_HARD_NO_GO"; exit 77; }
echo "RC8: QEMU full-system kernel=$KERNEL"
# Ubuntu packaged kernel is root-readable only; copy inside disposable runner.
KVER="$(basename "$KERNEL" | sed 's/^vmlinuz-//')"
sudo cp "$KERNEL" "$WORK/guest-vmlinuz"
sudo chmod 644 "$WORK/guest-vmlinuz"
KERNEL="$WORK/guest-vmlinuz"
cp "$(command -v busybox)" "$WORK/initramfs/bin/busybox"
# Stock Ubuntu kernels may ship virtio/ext4 as .ko.zst rather than built-ins.
# Copy only kernel-provided dependency modules, in modprobe load order, into
# guest initramfs. This VM doesn't borrow any host kernel state at runtime.
mkdir -p "$WORK/initramfs/mods"
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
echo "RC8: initramfs load-order kernel modules=$n"
gcc -O2 -static -Wall -Wextra "$ROOT/xray/lab/rc7_fullvm_cgroup_probe.c" -o "$WORK/initramfs/bin/rc7cgroup"
gcc -O2 -static -Wall -Wextra "$ROOT/xray/lab/rc7_guest_fdatasync.c" -o "$WORK/initramfs/bin/rc7fsync"
gcc -O2 -static -Wall -Wextra "$ROOT/xray/lab/rc8_guest_privdrop.c" -o "$WORK/initramfs/bin/rc8privdrop"
cp "$ROOT/xray/lab/rc8_fullvm_init" "$WORK/initramfs/init"
chmod 700 "$WORK/initramfs/init" "$WORK/initramfs/bin/rc7cgroup" "$WORK/initramfs/bin/rc7fsync" "$WORK/initramfs/bin/rc8privdrop" "$WORK/initramfs/bin/busybox"
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
echo "RC8: INDEPENDENT_VIRTUAL_DISK_FILES_PREPARED (not separate physical hardware)"
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
  if [ -f "$FIRST_LOG" ] && grep -q 'RC8_VM: POWER_CUT_POINT_AFTER_FSYNC_TWO_FILES' "$FIRST_LOG"; then
    SUCCESS=1;break
  fi
  if ! kill -0 "$FIRST_PID" 2>/dev/null; then break; fi
  sleep 1
done
if [ "$SUCCESS" != 1 ]; then
  echo "RC8: FIRST_BOOT_FAILED_OR_TIMED_OUT" >&2
  tail -65 "$FIRST_LOG" || true
  echo "RC8: QEMU_STARTUP_DIAGNOSTIC:"
  cat "$WORK/first-qemu-errors.log" || true
  exit 1
fi
echo "RC8: QEMU_POWER_CUT_AFTER_EXACTLY_TWO_FSYNC_WRITES"
kill -KILL "$FIRST_PID" || true
wait "$FIRST_PID" 2>/dev/null || true
trap - EXIT
# Take byte-for-byte snapshots of every active script AFTER the first crash.
# These are inspected after the second boot: fail-closed means ZERO writes.
mkdir -p "$WORK/active-before" "$WORK/active-after"
for name in S97 S98 S99 watchdog wifi_rules; do
  debugfs -R "dump /$name.sh $WORK/active-before/$name.sh" "$WORK/active.img" >/dev/null 2>&1
done
case "$SCENARIO" in
  journal-corrupt)
    printf 'CORRUPTED_NOT_STAGE_2\n' > "$WORK/corrupted-journal"
    debugfs -w -R "rm /journal" "$WORK/active.img" >/dev/null 2>&1
    debugfs -w -R "write $WORK/corrupted-journal /journal" "$WORK/active.img" >/dev/null 2>&1
    echo "RC8: INJECTED_CORRUPT_JOURNAL_IN_VIRTUAL_ACTIVE_DISK" ;;
  rescue-corrupt)
    printf 'CORRUPTED_FROZEN_RC1_SOURCE\n' > "$WORK/corrupted-source"
    debugfs -w -R "rm /originals/S97.sh" "$WORK/rescue.img" >/dev/null 2>&1
    debugfs -w -R "write $WORK/corrupted-source /originals/S97.sh" "$WORK/rescue.img" >/dev/null 2>&1
    echo "RC8: INJECTED_CORRUPT_SOURCE_IN_VIRTUAL_RESCUE_DISK" ;;
  baseline) ;;
esac
set +e
timeout --signal=KILL 170s qemu-system-x86_64 -nodefaults -nographic -no-reboot -machine pc,accel=tcg -m 512 -smp 1 \
  -kernel "$KERNEL" -initrd "$WORK/initramfs.img.gz" -monitor none -display none \
  -drive "file=$WORK/rescue.img,format=raw,if=virtio,cache=writeback" \
  -drive "file=$WORK/active.img,format=raw,if=virtio,cache=writeback" \
  -append "console=ttyS0 rdinit=/init rc7_stage=second panic=-1" \
  -serial "file:$SECOND_LOG" >"$WORK/second-qemu-errors.log" 2>&1
BOOT_EXIT=$?
set -e
if [ "$BOOT_EXIT" -ne 0 ]; then echo "RC8: SECOND_BOOT_EXIT=$BOOT_EXIT" >&2; fi
case "$SCENARIO" in
 baseline)
  grep -q 'RC8_VM: PREVIOUS_TWO_FILES_AND_JOURNAL_SURVIVED_QEMU_SIGKILL' "$SECOND_LOG"
  grep -q 'RC8_VM: EXACT_FIVE_RESCUE_ORIGINALS_VERIFIED' "$SECOND_LOG"
  grep -q 'RC8_VM: REBOOT_FULL_RESTORE_5_OF_5_PASS' "$SECOND_LOG"
  ;;
 journal-corrupt)
  grep -q 'RC8_VM: FAIL_CLOSED_CORRUPT_JOURNAL_NO_RESTORATION' "$SECOND_LOG"
  if grep -q 'RC8_VM: REBOOT_FULL_RESTORE_5_OF_5_PASS' "$SECOND_LOG"; then exit 1; fi
  ;;
 rescue-corrupt)
  grep -q 'RC8_VM: FAIL_CLOSED_CORRUPT_RESCUE_NO_RESTORATION' "$SECOND_LOG"
  if grep -q 'RC8_VM: REBOOT_FULL_RESTORE_5_OF_5_PASS' "$SECOND_LOG"; then exit 1; fi
  ;;
esac
if [ "$SCENARIO" != baseline ]; then
  for name in S97 S98 S99 watchdog wifi_rules; do
    debugfs -R "dump /$name.sh $WORK/active-after/$name.sh" "$WORK/active.img" >/dev/null 2>&1
    cmp "$WORK/active-before/$name.sh" "$WORK/active-after/$name.sh" || {
       echo "RC8: DANGEROUS_SECOND_BOOT_WROTE_ACTIVE_FILE $name" >&2; exit 1;
    }
  done
  echo "RC8: PASS_FAIL_CLOSED_CORRUPT_IMAGE_ZERO_ACTIVE_WRITES $SCENARIO"
fi
grep -q 'RC8_GUEST: EIGHT_REAL_UNPRIV_FORK_SETSID_EXEC_ESCAPE_DENIALS_PASS' "$FIRST_LOG"
grep -q 'RC8_GUEST: GUARDIAN_DENIES_RESTART_UNKNOWN_REPARENTED_DESCENDANT' "$FIRST_LOG"
grep -q 'RC8_GUEST: UNPRIVILEGED_ORPHAN_DRAINED_NO_RESTART_BEFORE_ABSENCE' "$FIRST_LOG"
grep -q 'RC8_GUEST: UNPRIVILEGED_CGROUP_ESCAPE_DENIED' "$FIRST_LOG"
grep -q 'RC8_GUEST: EIGHT_REAL_UNPRIV_FORK_SETSID_EXEC_ESCAPE_DENIALS_PASS' "$SECOND_LOG"
grep -q 'RC8_GUEST: GUARDIAN_DENIES_RESTART_UNKNOWN_REPARENTED_DESCENDANT' "$SECOND_LOG"
grep -q 'RC8_GUEST: UNPRIVILEGED_CGROUP_ESCAPE_DENIED' "$SECOND_LOG"
grep -q 'RC7_FSYNC: FILE_FDATASYNC_AND_DIRECTORY_FSYNC_PASS' "$FIRST_LOG"
if [ "$SCENARIO" = baseline ]; then
grep -q 'RC7_FSYNC: FILE_FDATASYNC_AND_DIRECTORY_FSYNC_PASS' "$SECOND_LOG"
fi
if grep -q 'RC7_GUEST: FAIL' "$FIRST_LOG" || grep -q 'RC7_GUEST: FAIL' "$SECOND_LOG"; then
  echo "RC8: GUEST_CGROUP_TEST_FAILED_NOT_A_CAPABILITY_LIMIT" >&2;exit 1
fi
if [ "$SCENARIO" = baseline ] && grep -q 'RC8_VM: FAIL' "$SECOND_LOG"; then echo "RC8: GUEST_FAILURE" >&2;exit 1;fi
CGROUP="CGROUP1_GUEST_BLOCKED_NO_GO"
if grep -q 'RC7_GUEST: REAL_CGROUP_V1_FORK_EXEC_DRAIN_PASS' "$SECOND_LOG" &&
   grep -q 'RC7_GUEST: REAL_TCP_UDP_FD_INODE_OWNER_PASS' "$SECOND_LOG" &&
   grep -q 'RC7_GUEST: REAL_EIGHT_GUARDIAN_FLOCK_RACE_ROUND_1_ONE_WINNER' "$SECOND_LOG" &&
   grep -q 'RC7_GUEST: REAL_EIGHT_GUARDIAN_FLOCK_RACE_ROUND_2_ONE_WINNER' "$SECOND_LOG"; then
   CGROUP="REAL_CGROUP_V1_GUEST_FORK_EXEC_AND_8X2_FLOCK_PASS"
fi
if [ "$CGROUP" = "CGROUP1_GUEST_BLOCKED_NO_GO" ] &&
   grep -q 'RC7_GUEST: REAL_CGROUP_V1_PIDS_MOUNT_PASS' "$SECOND_LOG"; then
  echo "RC8: cgroup mounted but real fork/socket/guardian proof missing" >&2
  exit 1
fi
if [ "$CGROUP" = "REAL_CGROUP_V1_GUEST_FORK_EXEC_AND_8X2_FLOCK_PASS" ]; then
  grep -q 'RC7_GUEST: REAL_DETACHED_EXEC_TCP_UDP' "$SECOND_LOG"
  grep -q 'RC7_GUEST: PRIVILEGED_CGROUP_ESCAPE_' "$SECOND_LOG"
  echo "RC8: GUEST_REAL_CGROUP1_FORK_EXEC_SOCKET_INODE_AND_8X2_FLOCK_VERIFIED"
  if grep -q 'RC7_GUEST: PRIVILEGED_CGROUP_ESCAPE_SUCCEEDED_HARD_NO_GO' "$SECOND_LOG"; then
    echo "RC8: IMPORTANT_PRIVILEGED_DESCENDANT_ESCAPED_CGROUP1; SEALING_NOT_PROVEN"
  fi
else
  grep -q 'RC8_VM: CGROUP_V1_UNAVAILABLE_HARD_NO_GO' "$SECOND_LOG"
fi
printf '%s\n' "$CGROUP" >"$WORK/cgroup-disposition.txt"
if [ "$SCENARIO" = baseline ]; then
  echo "RC8: PASS_DISPOSABLE_QEMU_TWO_BOOT_POWERLOSS_RESCUE_5_OF_5"
else
  echo "RC8: PASS_GUEST_REBOOT_CORRUPTION_HARD_NO_GO_$SCENARIO"
fi
echo "RC8: $CGROUP"
echo "RC8: HARD_NO_GO_PHYSICAL_KEENETIC_RUNTIME_CGROUP_BOOT_USB_TPROXY"
