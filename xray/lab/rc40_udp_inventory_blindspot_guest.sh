#!/bin/sh
# RC40: disposable MIPS Linux4.9 real xt_TPROXY FIRST ingress cutover.
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
 echo RC40_GUEST_HARD_NO_GO_IP_FORWARDING_ENABLED;exit 2;
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
 echo RC40_GUEST_HARD_NO_GO_TPROXY_LISTENERS_NOT_READY
 /bin/busybox tail -n 55 /lab/legacy.log /lab/candidate.log
 exit 2
fi
# Sample identity only after BOTH MIPS processes expose their TCP/UDP/API
# listeners. An early /proc/$pid/stat read races exec and transient failures.
test -r /proc/"$old"/stat && test -r /proc/"$new"/stat || {
 echo RC40_GUEST_HARD_NO_GO_LISTENER_WITHOUT_PROCESS_IDENTITY;exit 2;
}
old_ticks=$(/bin/busybox awk '{print $22}' /proc/$old/stat)
new_ticks=$(/bin/busybox awk '{print $22}' /proc/$new/stat)
test -n "$old_ticks" && test -n "$new_ticks" && test "$old_ticks" -gt 0 && test "$new_ticks" -gt 0 || {
 echo RC40_GUEST_HARD_NO_GO_EMPTY_PROCESS_STARTTICKS;exit 2;
}
for p in "$old" "$new";do
 uid=$(/bin/busybox awk '/^Uid:/ {print $2}' /proc/$p/status)
 caps=$(/bin/busybox awk '/^CapEff:/ {print $2}' /proc/$p/status)
 test "$uid" = 65534 && test "$caps" = 0000000000002000 || {
   echo RC40_GUEST_HARD_NO_GO_XRAY_PRIVILEGE;exit 2;
 }
done
/bin/busybox grep -Fq 'no_new_privs=1' /lab/legacy.log
/bin/busybox grep -Fq 'no_new_privs=1' /lab/candidate.log
# This is a deliberate NEGATIVE acceptance test. No TPROXY cutover here.
# All sysctls are INSIDE the disposable MIPS49 guest, never a real router.
for key in nf_conntrack_udp_timeout nf_conntrack_udp_timeout_stream;do
 path="/proc/sys/net/netfilter/$key"
 test -w "$path" || { echo "RC40_HARD_NO_GO_NO_KERNEL_TIMEOUT_SYSCTL_$key";exit 3; }
 echo 3 >"$path"
 test "$(/bin/busybox cat "$path")" = 3 || {
  echo RC40_HARD_NO_GO_KERNEL_TIMEOUT_READBACK_FAILED;exit 3;
 }
done
echo RC40_GUEST_CONNTRACK_UDP_TIMEOUTS_THREE_SECONDS_CONFIRMED
# Source/destination known only to the isolated synthetic network fixture.
# Packet was sent by host AFTER this READY marker; require positive kernel
# conntrack record while it is still present, not just an iptables counter.
echo RC40_GUEST_READY_TO_PRIME_IDLE_UDP
present=0
for n in $(/bin/busybox seq 1 80);do
 if /bin/busybox grep -E 'udp.*src=10\.77\.0\.1 dst=10\.77\.0\.3.*dport=19301' /proc/net/nf_conntrack >/lab/rc36-before 2>/dev/null;then
  present=1;break
 fi
 /bin/busybox sleep 0.1
done
if [ "$present" != 1 ];then
 echo RC40_HARD_NO_GO_INITIAL_CONNTRACK_ENTRY_NEVER_OBSERVED
 exit 4
fi
test "$(/bin/busybox grep -c . /lab/rc36-before)" = 1 || {
 echo RC40_HARD_NO_GO_UNEXPECTED_CONCURRENT_CONNTRACK_ENTRIES;exit 4;
}
# Identify exact source port from the independently verified first
# conntrack entry. Use it only for correlating *Xray's own debug logs*,
# never as evidence that kernel conntrack is a complete association map.
old_source_port=$(/bin/busybox awk '{
 for(i=1;i<NF-2;i++) if($i=="src=10.77.0.1" && $(i+1)=="dst=10.77.0.3") {
  p=$(i+2); sub(/^sport=/,"",p); print p; exit
 }
}' /lab/rc36-before)
case "$old_source_port" in ''|*[!0-9]*) echo RC40_HARD_NO_GO_INVALID_INITIAL_UDP_PORT;exit 4;;esac
log_token="processing connection from: 10.77.0.1:$old_source_port"
one=0
for n in $(/bin/busybox seq 1 35);do
 count=$(/bin/busybox grep -Fc "$log_token" /lab/legacy.log || true)
 if [ "$count" = 1 ];then one=1;break;fi
 /bin/busybox sleep 0.1
done
if [ "$one" != 1 ];then
 echo RC40_HARD_NO_GO_MISSING_FIRST_XRAY_INTERNAL_UDP_DISPATCH
 /bin/busybox tail -n 60 /lab/legacy.log
 exit 4
fi
echo RC40_GUEST_FIRST_XRAY_UDP_WORKER_PROCESS_ONCE sourceport="$old_source_port"
echo RC40_GUEST_REAL_OLD_UDP_CONNTRACK_ENTRY_WITNESSED
# A previous UDP association now sends ZERO packets. Poll until the
# native nf_conntrack entry disappears, without touching PREROUTING.
expired=0
for n in $(/bin/busybox seq 1 90);do
 if ! /bin/busybox grep -E 'udp.*src=10\.77\.0\.1 dst=10\.77\.0\.3.*dport=19301' /proc/net/nf_conntrack >/lab/rc36-after 2>/dev/null;then
  expired=1;break
 fi
 /bin/busybox sleep 0.2
done
if [ "$expired" != 1 ];then
 echo RC40_HARD_NO_GO_UDP_CONNTRACK_EXPIRY_NOT_OBSERVED
 exit 4
fi
test ! -s /lab/rc36-after || { echo RC40_HARD_NO_GO_EXPIRY_READBACK;exit 4; }
test "$(/bin/busybox awk '{print $22}' /proc/$old/stat)" = "$old_ticks" || exit 4
test "$(/bin/busybox awk '{print $22}' /proc/$new/stat)" = "$new_ticks" || exit 4
# No owner transfer: freeze has NOT been proved. Releasing a candidate
# ingress change here would steal the expired but possibly live Xray UDP flow.
echo RC40_GUEST_KERNEL_OLD_UDP_CONNTRACK_EXPIRED_WHILE_BOTH_XRAY_PIDS_UNCHANGED
/sbin/iptables -t mangle -S PREROUTING >/lab/rules-no-cutover
test "$(/bin/busybox grep -c -- '-j TPROXY' /lab/rules-no-cutover)" = 2 || {
 echo RC40_HARD_NO_GO_NETFILTER_CHANGED_DURING_NEGATIVE_TEST;exit 5;
}
echo RC40_GUEST_FAIL_CLOSED_NO_NEW_CANDIDATE_TPROXY_RULES
# A has an Xray udpWorker entry; B socket exists on host but has NEVER
# sent a packet. Both have absent kernel conntrack at this snapshot.
# This is a negative authority witness, not a cutover or freeze.
if /bin/busybox grep -E 'udp.*src=10\.77\.0\.1 dst=10\.77\.0\.3.*dport=19301' /proc/net/nf_conntrack >/lab/rc40-empty 2>/dev/null;then
 echo RC40_HARD_NO_GO_CONNTRACK_NONEMPTY_AT_SILENT_SNAPSHOT;exit 6
fi
boot_id=$(/bin/busybox cat /proc/sys/kernel/random/boot_id)
test -n "$boot_id" || exit 6
test "$( /bin/busybox grep -Fc "$log_token" /lab/legacy.log || true )" = 1 || {
 echo RC40_HARD_NO_GO_LEGACY_OWNER_LOG_NOT_ONE;exit 6
}
echo "RC40_GUEST_TWO_SOCKET_STATES_BOTH_ABSENT_FROM_KERNEL_CONNTRACK boot=$boot_id owner=$old ticks=$old_ticks"
echo RC40_GUEST_SNAPSHOT_READY_OLD_A_LIVE_IN_XRAY_B_NEVER_DISPATCHED
# Host now sends A and B in that order and requires exact independent
# backend UDP responses. A must reuse its process; B must dispatch anew.
observed=0
for n in $(/bin/busybox seq 1 120);do
 total=$(/bin/busybox grep -Fc 'processing connection from: 10.77.0.1:' /lab/legacy.log || true)
 a_count=$(/bin/busybox grep -Fc "$log_token" /lab/legacy.log || true)
 if [ "$a_count" != 1 ];then
   echo RC40_HARD_NO_GO_OLD_XRAY_UDP_ASSOCIATION_NOT_REUSED
   exit 7
 fi
 if [ "$total" = 2 ];then observed=1;break;fi
 if [ "$total" -gt 2 ];then
   echo RC40_HARD_NO_GO_EXTRA_UDP_OWNER_DISPATCH;exit 7
 fi
 /bin/busybox sleep 0.1
done
if [ "$observed" != 1 ];then
 echo RC40_HARD_NO_GO_NEVER_USED_SOCKET_NEW_DISPATCH_MISSING;exit 7
fi
new_record=$(/bin/busybox grep -F 'processing connection from: 10.77.0.1:' /lab/legacy.log | /bin/busybox grep -Fv "$log_token" | /bin/busybox tail -n 1)
new_port=$(echo "$new_record" | /bin/busybox sed -n 's/.*processing connection from: 10\.77\.0\.1:\([0-9][0-9]*\).*/\1/p')
case "$new_port" in ''|*[!0-9]*) echo RC40_HARD_NO_GO_NEW_UDP_SOURCE_PORT_PARSE;exit 7;;esac
test "$new_port" != "$old_source_port" || exit 7
test "$(/bin/busybox awk '{print $22}' /proc/$old/stat)" = "$old_ticks" || exit 7
test "$(/bin/busybox awk '{print $22}' /proc/$new/stat)" = "$new_ticks" || exit 7
test "$(/bin/busybox cat /proc/sys/kernel/random/boot_id)" = "$boot_id" || exit 7
/sbin/iptables -t mangle -S PREROUTING >/lab/rc40-after-rules
test "$(/bin/busybox grep -c -- '-j TPROXY' /lab/rc40-after-rules)" = 2 || {
 echo RC40_HARD_NO_GO_UNAPPROVED_KERNEL_CUTOVER;exit 7
}
echo "RC40_GUEST_LOG_OLD_REUSED_ONCE sourceport=$old_source_port"
echo "RC40_GUEST_LOG_NEW_DISPATCH_ONCE sourceport=$new_port"
echo RC40_GUEST_PROCESS_STARTTICKS_BOOT_UNCHANGED_NO_ROUTE_CUTOVER
echo RC40_GUEST_REAL_KERNEL_CONNTRACK_INSUFFICIENT_TO_INFER_PRIVATE_UDP_OWNER
echo RC40_PASS_TWO_REAL_MIPS49_UDP_SOCKET_STATES_KERNEL_SNAPSHOT_AMBIGUOUS
echo RC40_HARD_NO_GO_NO_ATOMIC_KERNEL_FREEZE_DURABLE_CAS_OR_PRIVILEGED_ROOT_FENCE
