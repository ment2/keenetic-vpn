#!/usr/bin/env bash
# Runs ONLY inside new disposable network namespace, no default route.
set -euo pipefail
test "$1" = --inside
W="$2";cd "$3"
test "$(ip -o link show | wc -l)" -eq 1
test -z "$(ip -4 route show default)"
ip link set lo up
unshare --net -- sleep 65 & child=$!
server=;client=
cleanup(){
 [ -z "$server" ] || kill "$server" 2>/dev/null || :
 [ -z "$client" ] || kill "$client" 2>/dev/null || :
 kill "$child" 2>/dev/null || :
 wait "$child" 2>/dev/null || :
}
trap cleanup EXIT
ip link add v42p type veth peer name v42c
ip addr add 10.42.0.1/24 dev v42p
ip link set v42p up
ip link set v42c netns "$child"
nsenter -t "$child" -n -- ip link set lo up
nsenter -t "$child" -n -- ip addr add 10.42.0.2/24 dev v42c
nsenter -t "$child" -n -- ip link set v42c up
test -z "$(ip -4 route show default)"
test -z "$(nsenter -t "$child" -n -- ip -4 route show default)"
test -z "$(nft list ruleset)"
nft list ruleset > "$W/original.nft"
before=$(sha256sum "$W/original.nft" | awk '{print $1}')
boot=$(cat /proc/sys/kernel/random/boot_id)
python3 -u xray/lab/rc42_netns_udp_endpoint.py server >"$W/server.log" 2>&1 & server=$!
for n in $(seq 1 100);do
 if grep -Fq RC42_SERVER_READY "$W/server.log";then break;fi
 sleep .04
done
grep -Fq RC42_SERVER_READY "$W/server.log"
server_ticks=$(awk '{print $22}' "/proc/$server/stat")
test "$server_ticks" -gt 0
mkfifo "$W/commands" "$W/events"
nsenter -t "$child" -n -- python3 -u xray/lab/rc42_netns_udp_endpoint.py client "$W/commands" "$W/events" >"$W/client.log" 2>&1 & client=$!
exec 3>"$W/commands"
exec 4<"$W/events"
IFS= read -r -t 8 ready <&4
case "$ready" in RC42_CLIENT_READY*) ;; *) echo RC42_HARD_NO_GO_CLIENT_NOT_READY;exit 8;;esac
client_ticks=$(awk '{print $22}' "/proc/$client/stat")
test "$client_ticks" -gt 0
echo "$ready" | tee -a "$W/summary.log"
echo BEFORE >&3
IFS= read -r -t 8 receipt <&4
case "$receipt" in RC42_CLIENT_BEFORE_EXACT_ECHO*) ;; *) echo RC42_HARD_NO_GO_BEFORE_PACKET;exit 9;;esac
echo "$receipt" | tee -a "$W/summary.log"
python3 -m xray.lab.rc42_fsync_generation_cas begin --root "$W/journal" --boot "$boot" --sha "$before" --pid "$server" --ticks "$server_ticks" | tee -a "$W/summary.log"
nft -f - <<'NFT'
table inet rc42 {
 chain input {
  type filter hook input priority -100; policy accept;
  iifname "v42p" ip saddr 10.42.0.2 ip daddr 10.42.0.1 udp dport 19542 counter drop
 }
}
NFT
nft -a list ruleset > "$W/frozen.nft"
grep -Fq 'dport 19542' "$W/frozen.nft"
frozen=$(sha256sum "$W/frozen.nft" | awk '{print $1}')
test "$frozen" != "$before"
python3 -m xray.lab.rc42_fsync_generation_cas advance --root "$W/journal" --expected 1 --old-phase ORIGINAL --new-phase FROZEN_DROP --boot "$boot" --sha "$before" --new-sha "$frozen" --pid "$server" --ticks "$server_ticks" | tee -a "$W/summary.log"
echo FROZEN >&3
IFS= read -r -t 8 receipt <&4
test "$receipt" = RC42_CLIENT_FROZEN_PACKET_TIMED_OUT_IN_REAL_KERNEL
echo "$receipt" | tee -a "$W/summary.log"
nft -a list chain inet rc42 input > "$W/packet-counter.log"
grep -Eq 'counter packets [1-9][0-9]* bytes [1-9][0-9]* drop' "$W/packet-counter.log"
! grep -Fq 'RC42_SERVER_RECEIVED RC42-FROZEN' "$W/server.log"
echo RC42_REAL_KERNEL_NFT_DROP_PACKET_TIMEOUT | tee -a "$W/summary.log"
nft delete table inet rc42
nft list ruleset > "$W/restored.nft"
cmp "$W/original.nft" "$W/restored.nft"
restored=$(sha256sum "$W/restored.nft" | awk '{print $1}')
test "$before" = "$restored"
python3 -m xray.lab.rc42_fsync_generation_cas advance --root "$W/journal" --expected 2 --old-phase FROZEN_DROP --new-phase RESTORED --boot "$boot" --sha "$frozen" --new-sha "$restored" --pid "$server" --ticks "$server_ticks" | tee -a "$W/summary.log"
echo AFTER >&3
IFS= read -r -t 8 receipt <&4
case "$receipt" in RC42_CLIENT_AFTER_EXACT_ECHO*) ;; *) echo RC42_HARD_NO_GO_AFTER_PACKET;exit 12;;esac
echo "$receipt" | tee -a "$W/summary.log"
test "$(awk '{print $22}' "/proc/$server/stat")" = "$server_ticks"
test "$(awk '{print $22}' "/proc/$client/stat")" = "$client_ticks"
test "$(cat /proc/sys/kernel/random/boot_id)" = "$boot"
grep -Fq 'RC42_SERVER_RECEIVED RC42-BEFORE' "$W/server.log"
grep -Fq 'RC42_SERVER_RECEIVED RC42-AFTER' "$W/server.log"
echo RC42_REAL_KERNEL_ORIGINAL_RULESET_EXACTLY_RESTORED | tee -a "$W/summary.log"
echo RC42_REAL_SOCKET_INODE_COOKIE_PID_STABLE_AFTER_ROLLBACK | tee -a "$W/summary.log"
echo RC42_HARD_NO_GO_DROP_IS_NOT_BUFFERED_ATOMIC_SESSION_FREEZE | tee -a "$W/summary.log"
echo STOP >&3
IFS= read -r -t 8 receipt <&4
test "$receipt" = RC42_CLIENT_STOPPED
