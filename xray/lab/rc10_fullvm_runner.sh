#!/usr/bin/env bash
# RC7 disposable full-system two-reboot test. Never run on a router.
set -euo pipefail
ROOT="$(pwd)"
: "$RUNNER_TEMP"
SCENARIO="${RC10_SCENARIO:-baseline}"
case "$SCENARIO" in baseline|rescue-missing) ;; *) echo "RC10: bad scenario" >&2; exit 2;; esac
WORK="$RUNNER_TEMP/xray-v30-rc10-fullvm-$SCENARIO"
test ! -e "$WORK"
mkdir -p "$WORK"/initramfs/bin "$WORK"/initramfs/proc "$WORK"/initramfs/sys "$WORK"/initramfs/dev "$WORK"/initramfs/run "$WORK"/initramfs/mnt "$WORK"/rescue "$WORK"/active
for command_name in qemu-system-x86_64 busybox debugfs gcc cpio mkfs.ext4; do command -v "$command_name"; done
: "${RC10_KERNEL_IMAGE:?requires preverified 4.9 kernel package in disposable runner}"
: "${RC10_KERNEL_VERSION:?requires exact 4.9 uname version}"
: "${RC10_MODULE_ROOT:?requires extracted archived Debian kernel modules}"
KERNEL="$RC10_KERNEL_IMAGE"
test -s "$KERNEL" || { echo "RC10: NO_REAL_FULL_SYSTEM_KERNEL_HARD_NO_GO"; exit 77; }
case "$RC10_KERNEL_VERSION" in 4.9.*) ;; *) echo 'RC10: refused non-4.9 kernel';exit 78;; esac
echo "RC10: QEMU full-system archive kernel=$KERNEL version=$KVER"
# Ubuntu packaged kernel is root-readable only; copy inside disposable runner.
KVER="$RC10_KERNEL_VERSION"
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
  done < <(modprobe -d "$RC10_MODULE_ROOT" -S "$KVER" --show-depends "$modname")
done
echo "RC10: initramfs load-order kernel modules=$n"
gcc -O2 -static -Wall -Wextra "$ROOT/xray/lab/rc7_fullvm_cgroup_probe.c" -o "$WORK/initramfs/bin/rc7cgroup"
gcc -O2 -static -Wall -Wextra "$ROOT/xray/lab/rc7_guest_fdatasync.c" -o "$WORK/initramfs/bin/rc7fsync"
gcc -O2 -static -Wall -Wextra "$ROOT/xray/lab/rc8_guest_privdrop.c" -o "$WORK/initramfs/bin/rc8privdrop"
gcc -O2 -static -Wall -Wextra "$ROOT/xray/lab/rc9_guest_capwrap.c" -o "$WORK/initramfs/bin/rc9capwrap"
gcc -O2 -static -Wall -Wextra "$ROOT/xray/lab/rc9_guest_socket_cap_probe.c" -o "$WORK/initramfs/bin/rc9socket"
gcc -O2 -static -Wall -Wextra "$ROOT/xray/lab/rc9_guest_parent_crash.c" -o "$WORK/initramfs/bin/rc9owner"
if [ -z "$XRAY_NATIVE_BINARY" ] || [ ! -f "$XRAY_NATIVE_BINARY" ]; then echo "RC10: official binary unavailable"; exit 77; fi
cp "$XRAY_NATIVE_BINARY" "$WORK/initramfs/bin/xray"
mkdir -p "$WORK/initramfs/etc"
cat > "$WORK/initramfs/etc/xray.json" <<'JSON'
{
 "log":{"loglevel":"debug"},
 "inbounds":[{
  "tag":"isolated-tproxy","listen":"127.0.0.1","port":12345,"protocol":"dokodemo-door",
  "settings":{"network":"tcp,udp","followRedirect":true},
  "streamSettings":{"sockopt":{"tproxy":"tproxy"}}
 }],
 "outbounds":[{"tag":"deny-all","protocol":"blackhole","settings":{}}],
 "routing":{"rules":[{"type":"field","inboundTag":["isolated-tproxy"],"outboundTag":"deny-all"}]}
}
JSON
chmod 644 "$WORK/initramfs/etc/xray.json"
cp "$ROOT/xray/lab/rc10_fullvm_init" "$WORK/initramfs/init"
chmod 700 "$WORK/initramfs/init" "$WORK/initramfs/bin/rc7cgroup" "$WORK/initramfs/bin/rc7fsync" "$WORK/initramfs/bin/busybox"
chmod 755 "$WORK/initramfs/bin/rc8privdrop"
chmod 755 "$WORK/initramfs/bin/rc9capwrap" "$WORK/initramfs/bin/rc9socket" "$WORK/initramfs/bin/xray" "$WORK/initramfs/bin/rc9owner"  # must be executable AFTER dropping UID before exec
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
echo "RC10: INDEPENDENT_VIRTUAL_DISK_FILES_PREPARED (not separate physical hardware)"
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
  if [ -f "$FIRST_LOG" ] && grep -q 'RC10_VM: POWER_CUT_POINT_AFTER_FSYNC_TWO_FILES' "$FIRST_LOG"; then
    SUCCESS=1;break
  fi
  if ! kill -0 "$FIRST_PID" 2>/dev/null; then break; fi
  sleep 1
done
if [ "$SUCCESS" != 1 ]; then
  echo "RC10: FIRST_BOOT_FAILED_OR_TIMED_OUT" >&2
  tail -65 "$FIRST_LOG" || true
  echo "RC10: QEMU_STARTUP_DIAGNOSTIC:"
  cat "$WORK/first-qemu-errors.log" || true
  exit 1
fi
echo "RC10: QEMU_POWER_CUT_AFTER_EXACTLY_TWO_FSYNC_WRITES"
kill -KILL "$FIRST_PID" || true
wait "$FIRST_PID" 2>/dev/null || true
trap - EXIT
# Crash leaves journaled ext4 unclean. Journal replay can otherwise undo
# offline debugfs injections, silently producing a false positive. First
# recover the *disposable virtual* filesystems with e2fsck.
for disk in active rescue; do
  set +e
  e2fsck -fy "$WORK/$disk.img" >"$WORK/$disk-offline-fsck.log" 2>&1
  rc=$?
  set -e
  if [ "$rc" -gt 1 ]; then
    echo "RC10: offline ext4 fsck unsafe status=$rc $disk" >&2
    tail -20 "$WORK/$disk-offline-fsck.log"
    exit 1
  fi
done
# Take byte-for-byte snapshots of every active script AFTER the first crash.
# These are inspected after the second boot: fail-closed means ZERO writes.
mkdir -p "$WORK/active-before" "$WORK/active-after"
for name in S97 S98 S99 watchdog wifi_rules; do
  debugfs -R "dump /$name.sh $WORK/active-before/$name.sh" "$WORK/active.img" >/dev/null 2>&1
done
case "$SCENARIO" in
  rescue-missing)
    truncate -s 48M "$WORK/blank-rescue.img"
    mkfs.ext4 -q -F "$WORK/blank-rescue.img"
    echo "RC10: INJECTED_MISSING_RESCUE_CONTENT_VIRTUAL_DEVICE"
    ;;
  baseline) ;;

esac
SECOND_RESCUE=rescue
if [ "$SCENARIO" = rescue-missing ]; then SECOND_RESCUE=blank-rescue; fi
set +e
timeout --signal=KILL 170s qemu-system-x86_64 -nodefaults -nographic -no-reboot -machine pc,accel=tcg -m 512 -smp 1 \
  -kernel "$KERNEL" -initrd "$WORK/initramfs.img.gz" -monitor none -display none \
  -drive "file=$WORK/$SECOND_RESCUE.img,format=raw,if=virtio,cache=writeback" \
  -drive "file=$WORK/active.img,format=raw,if=virtio,cache=writeback" \
  -append "console=ttyS0 rdinit=/init rc7_stage=second panic=-1" \
  -serial "file:$SECOND_LOG" >"$WORK/second-qemu-errors.log" 2>&1
BOOT_EXIT=$?
set -e
if [ "$BOOT_EXIT" -ne 0 ]; then echo "RC10: SECOND_BOOT_EXIT=$BOOT_EXIT" >&2; fi
case "$SCENARIO" in
 baseline)
  grep -q 'RC10_VM: REBOOT_FULL_RESTORE_5_OF_5_PASS' "$SECOND_LOG"
  ;;
 rescue-missing)
  grep -q 'RC10_VM: FAIL_CLOSED_CORRUPT_RESCUE_NO_RESTORATION' "$SECOND_LOG"
  if grep -q 'RC10_VM: REBOOT_FULL_RESTORE_5_OF_5_PASS' "$SECOND_LOG"; then exit 1; fi
  ;;

esac
if [ "$SCENARIO" != baseline ]; then
  for name in S97 S98 S99 watchdog wifi_rules; do
    debugfs -R "dump /$name.sh $WORK/active-after/$name.sh" "$WORK/active.img" >/dev/null 2>&1
    cmp "$WORK/active-before/$name.sh" "$WORK/active-after/$name.sh" || {
       echo "RC10: DANGEROUS_SECOND_BOOT_WROTE_ACTIVE_FILE $name" >&2; exit 1;
    }
  done
  echo "RC10: PASS_FAIL_CLOSED_CORRUPT_IMAGE_ZERO_ACTIVE_WRITES $SCENARIO"
fi
grep -q 'RC10_VM: REAL_XRAY_PARENT_SIGKILL_PDEATHSIG_IDENTITY_AND_LISTENER_DRAIN_PASS' "$FIRST_LOG"
grep -q 'RC10_VM: REAL_XRAY_PARENT_SIGKILL_PDEATHSIG_IDENTITY_AND_LISTENER_DRAIN_PASS' "$SECOND_LOG"
grep -q 'RC10_VM: ACTUAL_LINUX49_GUEST_VERSION_CONFIRMED' "$FIRST_LOG"
grep -q 'RC10_VM: ACTUAL_LINUX49_GUEST_VERSION_CONFIRMED' "$SECOND_LOG"
grep -q 'RC10_VM: ACTUAL_XRAY_TRANSPARENT_LISTENER_CAP_NET_RAW_ONLY_UID65534_PASS' "$FIRST_LOG"
grep -q 'RC10_VM: ACTUAL_XRAY_TRANSPARENT_LISTENER_CAP_NET_RAW_ONLY_UID65534_PASS' "$SECOND_LOG"
grep -q 'RC9_SOCKET: REAL_IP_TRANSPARENT_TCP_UDP_DENIED_WITHOUT_CAPS_PASS' "$FIRST_LOG"
grep -q 'RC9_SOCKET: REAL_IP_TRANSPARENT_TCP_UDP_CAP_NET_RAW_ONLY_PASS' "$SECOND_LOG"
grep -q 'RC8_GUEST: PRIVILEGES_DROPPED_BEFORE_EXEC_IN_ALL_WORKERS' "$FIRST_LOG"
grep -q 'RC8_GUEST: EIGHT_REAL_UNPRIV_FORK_SETSID_EXEC_ESCAPE_DENIALS_PASS' "$FIRST_LOG"
grep -q 'RC8_GUEST: GUARDIAN_DENIES_RESTART_UNKNOWN_REPARENTED_DESCENDANT' "$FIRST_LOG"
grep -q 'RC8_GUEST: UNPRIVILEGED_ORPHAN_DRAINED_NO_RESTART_BEFORE_ABSENCE' "$FIRST_LOG"
grep -q 'RC8_GUEST: UNPRIVILEGED_CGROUP_ESCAPE_DENIED' "$FIRST_LOG"
grep -q 'RC8_GUEST: PRIVILEGES_DROPPED_BEFORE_EXEC_IN_ALL_WORKERS' "$SECOND_LOG"
grep -q 'RC8_GUEST: EIGHT_REAL_UNPRIV_FORK_SETSID_EXEC_ESCAPE_DENIALS_PASS' "$SECOND_LOG"
grep -q 'RC8_GUEST: GUARDIAN_DENIES_RESTART_UNKNOWN_REPARENTED_DESCENDANT' "$SECOND_LOG"
grep -q 'RC8_GUEST: UNPRIVILEGED_CGROUP_ESCAPE_DENIED' "$SECOND_LOG"
grep -q 'RC7_FSYNC: FILE_FDATASYNC_AND_DIRECTORY_FSYNC_PASS' "$FIRST_LOG"
if [ "$SCENARIO" = baseline ]; then
grep -q 'RC7_FSYNC: FILE_FDATASYNC_AND_DIRECTORY_FSYNC_PASS' "$SECOND_LOG"
fi
if grep -q 'RC7_GUEST: FAIL' "$FIRST_LOG" || grep -q 'RC7_GUEST: FAIL' "$SECOND_LOG"; then
  echo "RC10: GUEST_CGROUP_TEST_FAILED_NOT_A_CAPABILITY_LIMIT" >&2;exit 1
fi
if [ "$SCENARIO" = baseline ] && grep -q 'RC10_VM: FAIL' "$SECOND_LOG"; then echo "RC10: GUEST_FAILURE" >&2;exit 1;fi
CGROUP="CGROUP1_GUEST_BLOCKED_NO_GO"
if grep -q 'RC7_GUEST: REAL_CGROUP_V1_FORK_EXEC_DRAIN_PASS' "$SECOND_LOG" &&
   grep -q 'RC7_GUEST: REAL_TCP_UDP_FD_INODE_OWNER_PASS' "$SECOND_LOG" &&
   grep -q 'RC7_GUEST: REAL_EIGHT_GUARDIAN_FLOCK_RACE_ROUND_1_ONE_WINNER' "$SECOND_LOG" &&
   grep -q 'RC7_GUEST: REAL_EIGHT_GUARDIAN_FLOCK_RACE_ROUND_2_ONE_WINNER' "$SECOND_LOG"; then
   CGROUP="REAL_CGROUP_V1_GUEST_FORK_EXEC_AND_8X2_FLOCK_PASS"
fi
if [ "$CGROUP" = "CGROUP1_GUEST_BLOCKED_NO_GO" ] &&
   grep -q 'RC7_GUEST: REAL_CGROUP_V1_PIDS_MOUNT_PASS' "$SECOND_LOG"; then
  echo "RC10: cgroup mounted but real fork/socket/guardian proof missing" >&2
  exit 1
fi
if [ "$CGROUP" = "REAL_CGROUP_V1_GUEST_FORK_EXEC_AND_8X2_FLOCK_PASS" ]; then
  grep -q 'RC7_GUEST: REAL_DETACHED_EXEC_TCP_UDP' "$SECOND_LOG"
  grep -q 'RC7_GUEST: PRIVILEGED_CGROUP_ESCAPE_' "$SECOND_LOG"
  echo "RC10: GUEST_REAL_CGROUP1_FORK_EXEC_SOCKET_INODE_AND_8X2_FLOCK_VERIFIED"
  if grep -q 'RC7_GUEST: PRIVILEGED_CGROUP_ESCAPE_SUCCEEDED_HARD_NO_GO' "$SECOND_LOG"; then
    echo "RC10: IMPORTANT_PRIVILEGED_DESCENDANT_ESCAPED_CGROUP1; SEALING_NOT_PROVEN"
  fi
else
  grep -q 'RC10_VM: CGROUP_V1_UNAVAILABLE_HARD_NO_GO' "$SECOND_LOG"
fi
printf '%s\n' "$CGROUP" >"$WORK/cgroup-disposition.txt"
if [ "$SCENARIO" = baseline ]; then
  echo "RC10: PASS_REAL_LINUX49_XRAY_CAP_RAW_AND_5_OF_5_RESTORE"
else
  echo "RC10: PASS_LINUX49_MISSING_RESCUE_ZERO_WRITES"
fi
echo "RC10: $CGROUP"
echo "RC10: HARD_NO_GO_PHYSICAL_KEENETIC_RUNTIME_CGROUP_BOOT_USB_TPROXY"
