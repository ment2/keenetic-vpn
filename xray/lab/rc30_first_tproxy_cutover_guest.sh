#!/bin/sh
# RC30: disposable MIPS Linux4.9 real xt_TPROXY FIRST ingress cutover.
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
 echo RC30_GUEST_HARD_NO_GO_IP_FORWARDING_ENABLED;exit 2;
}
/sbin/iptables -t mangle -A PREROUTING -i eth1 -p tcp --dport 19301 -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000
/sbin/iptables -t mangle -A PREROUTING -i eth1 -p udp --dport 19301 -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000
/bin/rc9capwrap raw xray >/lab/legacy.log 2>&1 &
old=$!
/bin/rc30capwrap raw xray >/lab/candidate.log 2>&1 &
new=$!
old_ticks=$(/bin/busybox awk '{print $22}' /proc/$old/stat)
new_ticks=$(/bin/busybox awk '{print $22}' /proc/$new/stat)
test -n "$old_ticks" && test -n "$new_ticks" && test "$old_ticks" -gt 0 && test "$new_ticks" -gt 0
ready=0
for n in $(/bin/busybox seq 1 180); do
 if /bin/busybox grep -q ':3039 ' /proc/net/tcp /proc/net/tcp6 2>/dev/null && \
    /bin/busybox grep -q ':5749 ' /proc/net/tcp /proc/net/tcp6 2>/dev/null && \
    /bin/busybox cat /proc/net/udp /proc/net/udp6 2>/dev/null | /bin/busybox grep -q ':3039 ' && \
    /bin/busybox cat /proc/net/udp /proc/net/udp6 2>/dev/null | /bin/busybox grep -q ':5749 '; then ready=1;break;fi
 /bin/busybox kill -0 "$old" 2>/dev/null || break
 /bin/busybox kill -0 "$new" 2>/dev/null || break
 /bin/busybox sleep 0.1
done
if [ "$ready" != 1 ];then
 echo RC30_GUEST_HARD_NO_GO_TPROXY_LISTENERS_NOT_READY
 /bin/busybox tail -n 55 /lab/legacy.log /lab/candidate.log
 exit 2
fi
for p in "$old" "$new";do
 uid=$(/bin/busybox awk '/^Uid:/ {print $2}' /proc/$p/status)
 caps=$(/bin/busybox awk '/^CapEff:/ {print $2}' /proc/$p/status)
 test "$uid" = 65534 && test "$caps" = 0000000000002000 || {
   echo RC30_GUEST_HARD_NO_GO_XRAY_PRIVILEGE;exit 2;
 }
done
/bin/busybox grep -Fq 'no_new_privs=1' /lab/legacy.log
/bin/busybox grep -Fq 'no_new_privs=1' /lab/candidate.log
echo RC30_GUEST_OLD_AND_CANDIDATE_XRAY_TCP_UDP_READY
# Wait until each old-protocol rule sees at least one actual host packet.
baseline=0
for n in $(/bin/busybox seq 1 180);do
 /sbin/iptables -t mangle -xvnL PREROUTING >/lab/oldcount
 if /bin/busybox awk '($3=="TPROXY" && $4=="tcp" && $1+0>0){t=1} ($3=="TPROXY" && $4=="udp" && $1+0>0){u=1} END{exit(t&&u)?0:1}' /lab/oldcount;then
 baseline=1;break;fi
 /bin/busybox sleep 0.1
done
test "$baseline" = 1 || { echo RC30_GUEST_HARD_NO_GO_OLD_BASELINE_PACKETS;exit 3; }
# Deliberately pre-register exactly one lab TCP and one lab UDP old tuple.
# This is a controlled positive packet test, NOT safe generic classifier.
# Exact old source ports: TCP=21111 UDP=21112, from host 10.77.0.1.
/sbin/iptables -t mangle -I PREROUTING 1 -i eth1 -s 10.77.0.1 -p udp --sport 21112 --dport 19301 -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000
/sbin/iptables -t mangle -I PREROUTING 1 -i eth1 -p udp --dport 19301 -j TPROXY --on-port 22345 --tproxy-mark 0x40000000/0x40000000
/sbin/iptables -t mangle -I PREROUTING 1 -i eth1 -p tcp --dport 19301 --tcp-flags SYN,RST,ACK SYN -j TPROXY --on-port 22345 --tproxy-mark 0x40000000/0x40000000
/sbin/iptables -t mangle -I PREROUTING 1 -i eth1 -s 10.77.0.1 -p tcp --sport 21111 --dport 19301 -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000
# Check exact known split and fail closed on additional unknown changes.
/sbin/iptables -t mangle -S PREROUTING >/lab/rules-cutover
test "$(/bin/busybox grep -c -- '-j TPROXY' /lab/rules-cutover)" = 6 || { echo RC30_GUEST_HARD_NO_GO_RULE_COUNT;exit 3; }
gen=2
echo RC30_GUEST_NEW_ONLY_TUPLE_PINNED_CUTOVER_READY
# Require positive witness on all intended new/old TPROXY paths.
seen=0
for n in $(/bin/busybox seq 1 180);do
 /sbin/iptables -t mangle -xvnL PREROUTING >/lab/newcounts
 if /bin/busybox awk '($3=="TPROXY"){i++; if(i<=4 && $1+0>0) positive[i]=1} END{exit positive[1]&&positive[2]&&positive[3]&&positive[4]?0:1}' /lab/newcounts;then seen=1;break;fi
 /bin/busybox sleep 0.1
done
if [ "$seen" != 1 ];then
 echo RC30_GUEST_HARD_NO_GO_BOTH_TPROXY_OWNERS_NOT_WITNESSED
 echo RC30_GUEST_TPROXY_SPLIT_COUNTERS_DIAGNOSTIC
 /bin/busybox cat /lab/newcounts
 exit 4
fi
/bin/busybox sleep 1
test "$(/bin/busybox awk '{print $22}' /proc/$old/stat)" = "$old_ticks"
test "$(/bin/busybox awk '{print $22}' /proc/$new/stat)" = "$new_ticks"
test "$gen" -eq 2
# Strict expected six rules, four migration-only + two original.
test "$(/bin/busybox grep -c -- '-j TPROXY' /lab/rules-cutover)" = 6
for i in 1 2 3 4;do /sbin/iptables -t mangle -D PREROUTING 1;done
/sbin/iptables -t mangle -S PREROUTING >/lab/rules-rollback
test "$(/bin/busybox grep -c -- '-j TPROXY' /lab/rules-rollback)" = 2 || {
 echo RC30_GUEST_HARD_NO_GO_ROLLBACK_RULE_OWNERSHIP;exit 5;
}
gen=3
echo RC30_GUEST_CUTOVER_RULES_REMOVED_ROLLBACK_READY
/bin/busybox sleep 9
test "$gen" -eq 3
test "$(/bin/busybox awk '{print $22}' /proc/$old/stat)" = "$old_ticks"
test "$(/bin/busybox awk '{print $22}' /proc/$new/stat)" = "$new_ticks"
echo RC30_GUEST_TWO_XRAY_PID_STARTTICKS_UNCHANGED_GENERATION_CAS_SYNTHETIC
/bin/busybox cat /lab/newcounts
/bin/busybox tail -n 32 /lab/legacy.log /lab/candidate.log
echo RC30_GUEST_HARD_NO_GO_GENERIC_UDP_5TUPLE_FENCING_WATCHDOG_PHYSICAL
