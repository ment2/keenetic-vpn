#!/bin/sh
# RC22 disposable MIPS guest: observe direct bypass after parent-owned Xray death.
# NEVER used on a router. No external network. No production release claim.
set -eu
/bin/ip link set lo up
/bin/ip link set eth0 up
/bin/ip addr add 10.0.2.15/24 dev eth0
/bin/ip rule add fwmark 0x40000000/0x40000000 table 100 priority 20000
/bin/ip route add local 0.0.0.0/0 dev lo table 100
/sbin/iptables -t mangle -A PREROUTING -i eth0 -p tcp --dport 19191 -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000
/sbin/iptables -t mangle -A PREROUTING -i eth0 -p udp --dport 19191 -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000
echo 'RC22_GUEST: ISOLATED_TCP_UDP_TPROXY_RULES_READY'
/lab/echo >/lab/backend.log 2>&1 &
backend=$!
/bin/rc9capwrap raw xray >/lab/xray.log 2>&1 &
xraypid=$!
ready=0
for n in $(/bin/busybox seq 1 120); do
  tcp=$(/bin/busybox cat /proc/net/tcp /proc/net/tcp6 2>/dev/null || true)
  udp=$(/bin/busybox cat /proc/net/udp /proc/net/udp6 2>/dev/null || true)
  if printf '%s\n' "$tcp" | /bin/busybox grep -q ':3039 ' && \
     printf '%s\n' "$udp" | /bin/busybox grep -q ':3039 ' && \
     printf '%s\n' "$udp" | /bin/busybox grep -q ':4B5C '; then ready=1; break; fi
  if ! /bin/busybox kill -0 "$xraypid" 2>/dev/null; then break; fi
  /bin/busybox sleep 0.1
done
if [ "$ready" != 1 ]; then
  echo 'RC22_GUEST: HARD_NO_GO_BASELINE_SOCKET_NOT_READY'
  /bin/busybox cat /lab/xray.log
  exit 2
fi
uid=$(/bin/busybox awk '/^Uid:/ {print $2}' /proc/$xraypid/status)
caps=$(/bin/busybox awk '/^CapEff:/ {print $2}' /proc/$xraypid/status)
test "$uid" = 65534 && test "$caps" = 0000000000002000
/bin/busybox grep -Fq 'no_new_privs=1' /lab/xray.log
# Linux4.9 has no pidfd. Parent owns child and must not wait/reap until signal.
# start_ticks is checked twice but cannot certify production race-free fencing.
xticks=$(/bin/busybox awk '{print $22}' /proc/$xraypid/stat)
test -n "$xticks" && test "$xticks" -gt 0
echo 'RC22_GUEST: XRAY_READY_SEND_BASELINE'
backend_done=0
for n in $(/bin/busybox seq 1 180); do
  state=$(/bin/busybox awk '{print $3}' /proc/$backend/stat 2>/dev/null || true)
  if [ "$state" = Z ] || [ -z "$state" ]; then backend_done=1; break; fi
  /bin/busybox sleep 0.1
done
test "$backend_done" = 1 || { echo 'RC22_GUEST: HARD_NO_GO_BASELINE_BACKEND_DID_NOT_RECEIVE_BOTH'; exit 2; }
wait "$backend"
/bin/busybox grep -Fq 'RC19_GUEST: REAL_TCP_UDP_ECHO_BYTES_PASS' /lab/backend.log
echo 'RC22_GUEST: REAL_XRAY_TCP_UDP_BASELINE_BACKEND_PASS'
/sbin/iptables -t mangle -xvnL PREROUTING >/lab/counters-before
xticks2=$(/bin/busybox awk '{print $22}' /proc/$xraypid/stat 2>/dev/null || true)
test "$xticks" = "$xticks2" || { echo 'RC22_GUEST: HARD_NO_GO_XRAY_PID_REUSE_AMBIGUOUS'; exit 2; }
/bin/busybox kill -TERM "$xraypid"
stopped=0
for n in $(/bin/busybox seq 1 120); do
  tcp=$(/bin/busybox cat /proc/net/tcp /proc/net/tcp6 2>/dev/null || true)
  udp=$(/bin/busybox cat /proc/net/udp /proc/net/udp6 2>/dev/null || true)
  if ! printf '%s\n%s\n' "$tcp" "$udp" | /bin/busybox grep -q ':3039 '; then stopped=1; break; fi
  /bin/busybox sleep 0.1
done
test "$stopped" = 1 || { echo 'RC22_GUEST: HARD_NO_GO_XRAY_STILL_LISTENING'; exit 2; }
echo 'RC22_GUEST: XRAY_LISTENERS_GONE_AFTER_PARENT_OWNED_SIGNAL'
# Trap only test-owned fallback: this sentinel DID NOT exist while Xray ran.
# If any post-death packet hits the original destination, direct bypass exists.
# This synthetic sentinel intentionally tests the exact non-Xray fallback case.
/lab/echo-orig >/lab/sentinel.log 2>&1 &
sentinel=$!
sentinel_ready=0
for n in $(/bin/busybox seq 1 70); do
  if /bin/busybox grep -Fq 'RC19_GUEST: ECHO_SERVER_READY' /lab/sentinel.log 2>/dev/null; then sentinel_ready=1; break; fi
  if ! /bin/busybox kill -0 "$sentinel" 2>/dev/null; then break; fi
  /bin/busybox sleep 0.1
done
test "$sentinel_ready" = 1 || { echo 'RC22_GUEST: HARD_NO_GO_SENTINEL_BIND_NOT_READY'; /bin/busybox cat /lab/sentinel.log; exit 2; }
echo 'RC22_GUEST: POSTDEATH_SENTINEL_READY_SEND_PROBES'
/bin/busybox sleep 12
/sbin/iptables -t mangle -xvnL PREROUTING >/lab/counters-after
/bin/busybox cat /lab/sentinel.log
echo 'RC22_GUEST: MANGLE_COUNTERS_BEFORE'
/bin/busybox cat /lab/counters-before
echo 'RC22_GUEST: MANGLE_COUNTERS_AFTER'
/bin/busybox cat /lab/counters-after
# No success can be inferred if the probe failed to reach kernel TPROXY rules.
for proto in tcp udp; do
  before=$(/bin/busybox awk -v p="$proto" '$3=="TPROXY" && $4==p {print $1}' /lab/counters-before)
  after=$(/bin/busybox awk -v p="$proto" '$3=="TPROXY" && $4==p {print $1}' /lab/counters-after)
  test -n "$before" && test -n "$after" && test "$after" -gt "$before" || {
    echo "RC22_GUEST: HARD_NO_GO_POSTDEATH_PROBE_NOT_AT_TPROXY_$proto"
    exit 2
  }
done
if /bin/busybox grep -Eq 'RC19_GUEST: REAL_(TCP|UDP)_BYTES=25' /lab/sentinel.log; then
  echo 'RC22_GUEST: OBSERVED_DIRECT_FALLBACK_AFTER_XRAY_DEATH_HARD_NO_GO'
  exit 3
fi
echo 'RC22_GUEST: POSTDEATH_NO_SENTINEL_RECEIPT_BOUNDED_LAB_ONLY'
echo 'RC22_GUEST: HARD_NO_GO_HOST_UDP_RETURN_VENDOR_LEGACY_PHYSICAL_RESCUE'
