#!/bin/sh
# RC35: disposable MIPS Linux4.9 real xt_TPROXY FIRST ingress cutover.
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
 echo RC35_GUEST_HARD_NO_GO_IP_FORWARDING_ENABLED;exit 2;
}
/sbin/iptables -t mangle -A PREROUTING -i eth1 -p tcp --dport 19301 -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000
/sbin/iptables -t mangle -A PREROUTING -i eth1 -p udp --dport 19301 -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000
/bin/rc9capwrap raw xray >/lab/legacy.log 2>&1 &
old=$!
/bin/rc30capwrap raw xray >/lab/candidate.log 2>&1 &
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
 echo RC35_GUEST_HARD_NO_GO_TPROXY_LISTENERS_NOT_READY
 /bin/busybox tail -n 55 /lab/legacy.log /lab/candidate.log
 exit 2
fi
# Sample identity only after BOTH MIPS processes expose their TCP/UDP/API
# listeners. An early /proc/$pid/stat read races exec and transient failures.
test -r /proc/"$old"/stat && test -r /proc/"$new"/stat || {
 echo RC35_GUEST_HARD_NO_GO_LISTENER_WITHOUT_PROCESS_IDENTITY;exit 2;
}
old_ticks=$(/bin/busybox awk '{print $22}' /proc/$old/stat)
new_ticks=$(/bin/busybox awk '{print $22}' /proc/$new/stat)
test -n "$old_ticks" && test -n "$new_ticks" && test "$old_ticks" -gt 0 && test "$new_ticks" -gt 0 || {
 echo RC35_GUEST_HARD_NO_GO_EMPTY_PROCESS_STARTTICKS;exit 2;
}
for p in "$old" "$new";do
 uid=$(/bin/busybox awk '/^Uid:/ {print $2}' /proc/$p/status)
 caps=$(/bin/busybox awk '/^CapEff:/ {print $2}' /proc/$p/status)
 test "$uid" = 65534 && test "$caps" = 0000000000002000 || {
   echo RC35_GUEST_HARD_NO_GO_XRAY_PRIVILEGE;exit 2;
 }
done
/bin/busybox grep -Fq 'no_new_privs=1' /lab/legacy.log
/bin/busybox grep -Fq 'no_new_privs=1' /lab/candidate.log
# This is a deliberate NEGATIVE acceptance test. No TPROXY cutover here.
# All sysctls are INSIDE the disposable MIPS49 guest, never a real router.
for key in nf_conntrack_udp_timeout nf_conntrack_udp_timeout_stream;do
 path="/proc/sys/net/netfilter/$key"
 test -w "$path" || { echo "RC35_HARD_NO_GO_NO_KERNEL_TIMEOUT_SYSCTL_$key";exit 3; }
 echo 3 >"$path"
 test "$(/bin/busybox cat "$path")" = 3 || {
  echo RC35_HARD_NO_GO_KERNEL_TIMEOUT_READBACK_FAILED;exit 3;
 }
done
echo RC35_GUEST_CONNTRACK_UDP_TIMEOUTS_THREE_SECONDS_CONFIRMED
# Source/destination known only to the isolated synthetic network fixture.
# Packet was sent by host AFTER this READY marker; require positive kernel
# conntrack record while it is still present, not just an iptables counter.
echo RC35_GUEST_READY_TO_PRIME_IDLE_UDP
present=0
for n in $(/bin/busybox seq 1 80);do
 if /bin/busybox grep -E 'udp.*src=10\.77\.0\.1 dst=10\.77\.0\.3.*dport=19301' /proc/net/nf_conntrack >/lab/rc35-before 2>/dev/null;then
  present=1;break
 fi
 /bin/busybox sleep 0.1
done
if [ "$present" != 1 ];then
 echo RC35_HARD_NO_GO_INITIAL_CONNTRACK_ENTRY_NEVER_OBSERVED
 exit 4
fi
test "$(/bin/busybox grep -c . /lab/rc35-before)" = 1 || {
 echo RC35_HARD_NO_GO_UNEXPECTED_CONCURRENT_CONNTRACK_ENTRIES;exit 4;
}
echo RC35_GUEST_REAL_OLD_UDP_CONNTRACK_ENTRY_WITNESSED
# A previous UDP association now sends ZERO packets. Poll until the
# native nf_conntrack entry disappears, without touching PREROUTING.
expired=0
for n in $(/bin/busybox seq 1 90);do
 if ! /bin/busybox grep -E 'udp.*src=10\.77\.0\.1 dst=10\.77\.0\.3.*dport=19301' /proc/net/nf_conntrack >/lab/rc35-after 2>/dev/null;then
  expired=1;break
 fi
 /bin/busybox sleep 0.2
done
if [ "$expired" != 1 ];then
 echo RC35_HARD_NO_GO_UDP_CONNTRACK_EXPIRY_NOT_OBSERVED
 exit 4
fi
test ! -s /lab/rc35-after || { echo RC35_HARD_NO_GO_EXPIRY_READBACK;exit 4; }
test "$(/bin/busybox awk '{print $22}' /proc/$old/stat)" = "$old_ticks" || exit 4
test "$(/bin/busybox awk '{print $22}' /proc/$new/stat)" = "$new_ticks" || exit 4
# No owner transfer: freeze has NOT been proved. Releasing a candidate
# ingress change here would steal the expired but possibly live Xray UDP flow.
echo RC35_GUEST_KERNEL_OLD_UDP_CONNTRACK_EXPIRED_WHILE_BOTH_XRAY_PIDS_UNCHANGED
/sbin/iptables -t mangle -S PREROUTING >/lab/rules-no-cutover
test "$(/bin/busybox grep -c -- '-j TPROXY' /lab/rules-no-cutover)" = 2 || {
 echo RC35_HARD_NO_GO_NETFILTER_CHANGED_DURING_NEGATIVE_TEST;exit 5;
}
echo RC35_GUEST_FAIL_CLOSED_NO_NEW_CANDIDATE_TPROXY_RULES
# Host sends from the same held-open original socket only after expiry.
# Round-trip after expiry CANNOT independently prove the original internal
# Xray association survived: it might create a fresh one.
wait_reply=0
for n in $(/bin/busybox seq 1 70);do
 if /bin/busybox grep -E 'udp.*src=10\.77\.0\.1 dst=10\.77\.0\.3.*dport=19301' /proc/net/nf_conntrack >/lab/rc35-recreated 2>/dev/null;then
  wait_reply=1;break
 fi
 /bin/busybox sleep 0.1
done
if [ "$wait_reply" != 1 ];then
 echo RC35_HARD_NO_GO_OLD_UDP_REPLY_CONNTRACK_NOT_RECREATED
 exit 5
fi
echo RC35_GUEST_OLD_UDP_ASSOCIATION_RECOVERED_ONLY_WITHOUT_CUTOVER
echo RC35_PASS_REAL_MIPS49_NF_CONNTRACK_EXPIRY_DETECTED_AND_CUTOVER_REFUSED
echo RC35_HARD_NO_GO_NO_COMPLETE_XRAY_UDP_OWNER_OR_ATOMIC_FREEZE
