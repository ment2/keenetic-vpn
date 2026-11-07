#!/usr/bin/env bash
set -euo pipefail
test "$GITHUB_ACTIONS" = true
test -n "$RUNNER_TEMP"
test -n "$GITHUB_WORKSPACE"
W="$RUNNER_TEMP/rc44-native-tproxy"
test ! -e "$W"
mkdir -m 700 "$W"
export RC44_NINE="$W/nine.rules"
sudo --preserve-env=GITHUB_ACTIONS,RC44_NINE unshare --net -- bash -x xray/lab/rc44_tproxy_repair_netns.sh --inside "$W" "$GITHUB_WORKSPACE" | tee "$W/result.log"
for flag in RC44_REAL_NATIVE_KERNEL_TPROXY_TCP_UDP_PACKET_COUNTER_SOCKET_SUCCESS RC44_EXACT_ORIGINAL_KERNEL_MANGLE_RESTORED_AND_FAIL_CLOSED RC44_HARD_NO_GO_NATIVE_LINUX_IS_NOT_PHYSICAL_KENETIC;do
 grep -Fq "$flag" "$W/result.log"
done
echo RC44_DISPOSABLE_KERNEL_REPAIR_ROLLBACK_COMPLETE
