#!/bin/sh
# RC33: disposable MIPS Linux4.9 real xt_TPROXY FIRST ingress cutover.
# Only pinned synthetic old source tuples are known; NO generic UDP classifier.
set -eu
/bin/ip link set lo up
/bin/ip link set eth0 up
/bin/ip addr add 10.0.2.15/24 dev eth0
/bin/ip link set eth1 up
/bin/ip addr add 10.77.0.2/24 dev eth1
/bin/ip rule add fwmark 0x40000000/0x40000000 table 100 priority 20000
/bin/ip route add local 0.0.0.0/0 dev lo table 100
# Minimal MIPS49 initramfs intentionally has no iptable_filter. Forbid
# kernel forwarding instead of requiring a module absent from this fixture.
test "$(/bin/busybox cat /proc/sys/net/ipv4/ip_forward)" = 0 || {
 echo RC33_GUEST_HARD_NO_GO_IP_FORWARDING_ENABLED;exit 2;
}
/sbin/iptables -t mangle -A PREROUTING -i eth1 -p tcp --dport 19301 -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000
/sbin/iptables -t mangle -A PREROUTING -i eth1 -p udp --dport 19301 -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000
/bin/rc9capwrap raw xray >/lab/legacy.log 2>&1 &
old=$!
/bin/rc33capwrap raw xray >/lab/candidate.log 2>&1 &
new=$!
ready=0
for n in $(/bin/busybox seq 1 180); do
 if /bin/busybox grep -q ':3039 ' /proc/net/tcp /proc/net/tcp6 2>/dev/null && \
    /bin/busybox grep -q ':5530 ' /proc/net/tcp /proc/net/tcp6 2>/dev/null && \
    /bin/busybox grep -q ':5749 ' /proc/net/tcp /proc/net/tcp6 2>/dev/null && \
    /bin/busybox cat /proc/net/udp /proc/net/udp6 2>/dev/null | /bin/busybox grep -q ':3039 ' && \
    /bin/busybox cat /proc/net/udp /proc/net/udp6 2>/dev/null | /bin/busybox grep -q ':5749 '; then ready=1;break;fi
 /bin/busybox kill -0 "$old" 2>/dev/null || break
 /bin/busybox kill -0 "$new" 2>/dev/null || break
 /bin/busybox sleep 0.1
done
if [ "$ready" != 1 ];then
 echo RC33_GUEST_HARD_NO_GO_TPROXY_LISTENERS_NOT_READY
 /bin/busybox tail -n 55 /lab/legacy.log /lab/candidate.log
 exit 2
fi
# Sample identity only after BOTH MIPS processes expose their TCP/UDP/API
# listeners. An early /proc/$pid/stat read races exec and transient failures.
test -r /proc/"$old"/stat && test -r /proc/"$new"/stat || {
 echo RC33_GUEST_HARD_NO_GO_LISTENER_WITHOUT_PROCESS_IDENTITY;exit 2;
}
old_ticks=$(/bin/busybox awk '{print $22}' /proc/$old/stat)
new_ticks=$(/bin/busybox awk '{print $22}' /proc/$new/stat)
test -n "$old_ticks" && test -n "$new_ticks" && test "$old_ticks" -gt 0 && test "$new_ticks" -gt 0 || {
 echo RC33_GUEST_HARD_NO_GO_EMPTY_PROCESS_STARTTICKS;exit 2;
}
for p in "$old" "$new";do
 uid=$(/bin/busybox awk '/^Uid:/ {print $2}' /proc/$p/status)
 caps=$(/bin/busybox awk '/^CapEff:/ {print $2}' /proc/$p/status)
 test "$uid" = 65534 && test "$caps" = 0000000000002000 || {
   echo RC33_GUEST_HARD_NO_GO_XRAY_PRIVILEGE;exit 2;
 }
done
/bin/busybox grep -Fq 'no_new_privs=1' /lab/legacy.log
/bin/busybox grep -Fq 'no_new_privs=1' /lab/candidate.log
/lab/rc33-observer 2 eth1 >/lab/observer.log 2>&1 &
observer=$!
watcher=0
for n in $(/bin/busybox seq 1 70); do
 if /bin/busybox grep -Fq RC33_OBSERVER_PACKET_SOCKET_READY_ETH1 /lab/observer.log 2>/dev/null;then watcher=1;break;fi
 /bin/busybox kill -0 "$observer" 2>/dev/null || break
 /bin/busybox sleep 0.1
done
if [ "$watcher" != 1 ];then echo RC33_GUEST_HARD_NO_GO_PACKET_OBSERVER_NOT_READY;exit 2;fi
echo RC33_GUEST_OLD_AND_API_ENABLED_CANDIDATE_XRAY_TCP_UDP_READY
# Wait until each old-protocol rule sees at least one actual host packet.
baseline=0
for n in $(/bin/busybox seq 1 180);do
 /sbin/iptables -t mangle -xvnL PREROUTING >/lab/oldcount
 if /bin/busybox awk '($3=="TPROXY" && $4=="tcp" && $1+0>0){t=1} ($3=="TPROXY" && $4=="udp" && $1+0>0){u=1} END{exit(t&&u)?0:1}' /lab/oldcount;then
 baseline=1;break;fi
 /bin/busybox sleep 0.1
done
test "$baseline" = 1 || { echo RC33_GUEST_HARD_NO_GO_OLD_BASELINE_PACKETS;exit 3; }
# Collect actual UDP packet 5-tuples on eth1, not hardcoded source ports.
# Fail closed if any observed old flow is missing or has inconsistent boot ID.
wait "$observer" || { echo RC33_GUEST_HARD_NO_GO_OBSERVER_FAILED; /bin/busybox cat /lab/observer.log;exit 3; }
test -s /lab/rc33-udp-flows.txt || { echo RC33_GUEST_HARD_NO_GO_FLOW_MAP_MISSING;exit 3; }
boot_id=$(/bin/busybox cat /proc/sys/kernel/random/boot_id)
mapheader=$(/bin/busybox head -n 1 /lab/rc33-udp-flows.txt)
test "$mapheader" = "boot=$boot_id generation=1 interface=eth1 count=2" || {
 echo RC33_GUEST_HARD_NO_GO_BOOT_GENERATION_FLOW_CAS_MISMATCH;exit 3;
}
# Candidate broad UDP installed FIRST, then narrower discovered old UDP pins
# inserted ABOVE it; TCP new SYN goes to candidate while established old stays.
# All rules exist only within the disposable MIPS guest.
 /sbin/iptables -t mangle -I PREROUTING 1 -i eth1 -p udp --dport 19301 -j TPROXY --on-port 22345 --tproxy-mark 0x40000000/0x40000000
flow_count=0
while read -r src sport dst dport;do
 case "$src" in boot=*)continue;;esac
 test "$src" = 10.77.0.1 && test "$dst" = 10.77.0.3 && test "$dport" = 19301 || {
  echo RC33_GUEST_HARD_NO_GO_FOREIGN_OR_MODIFIED_5TUPLE;exit 3;
 }
 case "$sport" in ''|*[!0-9]*)echo RC33_GUEST_HARD_NO_GO_BAD_SOURCE_PORT;exit 3;;esac
 test "$sport" -gt 1023 && test "$sport" -le 65535 || exit 3
 /sbin/iptables -t mangle -I PREROUTING 1 -i eth1 -s "$src" -d "$dst" -p udp --sport "$sport" --dport "$dport" -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000
 flow_count=$((flow_count+1))
done </lab/rc33-udp-flows.txt
test "$flow_count" = 2 || { echo RC33_GUEST_HARD_NO_GO_DYNAMIC_FLOW_COUNT;exit 3; }
/sbin/iptables -t mangle -I PREROUTING 1 -i eth1 -p tcp --dport 19301 --tcp-flags SYN,RST,ACK SYN -j TPROXY --on-port 22345 --tproxy-mark 0x40000000/0x40000000
/sbin/iptables -t mangle -I PREROUTING 1 -i eth1 -s 10.77.0.1 -p tcp --sport 21111 --dport 19301 -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000
/sbin/iptables -t mangle -S PREROUTING >/lab/rules-cutover
expected_rules=$((flow_count+5))
test "$(/bin/busybox grep -c -- '-j TPROXY' /lab/rules-cutover)" = "$expected_rules" || {
 echo RC33_GUEST_HARD_NO_GO_RULE_COUNT;exit 3;
}
echo RC33_GUEST_DYNAMIC_UDP_FLOW_MAP_DISCOVERED_AND_PINNED count="$flow_count" boot="$boot_id"
gen=2
echo RC33_GUEST_NEW_ONLY_TUPLE_PINNED_CUTOVER_READY
# Require positive witness on all intended new/old TPROXY paths.
seen=0
for n in $(/bin/busybox seq 1 180);do
 /sbin/iptables -t mangle -xvnL PREROUTING >/lab/newcounts
 if /bin/busybox awk '($3=="TPROXY"){i++;if(i<=5 && $1+0>0)positive[i]=1} END{exit positive[1]&&positive[2]&&positive[3]&&positive[4]&&positive[5]?0:1}' /lab/newcounts;then seen=1;break;fi
 /bin/busybox sleep 0.1
done
if [ "$seen" != 1 ];then
 echo RC33_GUEST_HARD_NO_GO_BOTH_TPROXY_OWNERS_NOT_WITNESSED
 echo RC33_GUEST_TPROXY_SPLIT_COUNTERS_DIAGNOSTIC
 /bin/busybox cat /lab/newcounts
 exit 4
fi
/bin/busybox sleep 1
test "$(/bin/busybox awk '{print $22}' /proc/$old/stat)" = "$old_ticks"
test "$(/bin/busybox awk '{print $22}' /proc/$new/stat)" = "$new_ticks"
test "$gen" -eq 2
# Strict expected six rules, four migration-only + two original.
test "$(/bin/busybox grep -c -- '-j TPROXY' /lab/rules-cutover)" = "$expected_rules"
# Re-validate boot + generation before destructive rollback.
test "$(/bin/busybox cat /proc/sys/kernel/random/boot_id)" = "$boot_id" && test "$gen" = 2 || { echo RC33_GUEST_HARD_NO_GO_STALE_CAS_ROLLBACK;exit 5; }
for i in $(/bin/busybox seq 1 "$((flow_count+3))");do /sbin/iptables -t mangle -D PREROUTING 1;done
/sbin/iptables -t mangle -S PREROUTING >/lab/rules-rollback
test "$(/bin/busybox grep -c -- '-j TPROXY' /lab/rules-rollback)" = 2 || {
 echo RC33_GUEST_HARD_NO_GO_ROLLBACK_RULE_OWNERSHIP;exit 5;
}
gen=3
echo RC33_GUEST_CUTOVER_RULES_REMOVED_ROLLBACK_READY
/bin/busybox sleep 9
test "$gen" -eq 3
test "$(/bin/busybox awk '{print $22}' /proc/$old/stat)" = "$old_ticks"
test "$(/bin/busybox awk '{print $22}' /proc/$new/stat)" = "$new_ticks"
echo RC33_GUEST_TWO_XRAY_PID_STARTTICKS_UNCHANGED_GENERATION_CAS_SYNTHETIC
/bin/busybox cat /lab/observer.log
/bin/busybox cat /lab/newcounts
/bin/busybox tail -n 32 /lab/legacy.log /lab/candidate.log
echo RC33_GUEST_HARD_NO_GO_GENERIC_UDP_5TUPLE_FENCING_WATCHDOG_PHYSICAL
