#!/bin/sh
# RC21 disposable guest-only real MIPS Xray 26.2.6 CAP_NET_RAW, no exterior route.
set -eu
/bin/ip link set lo up
/bin/ip link set eth0 up
/bin/ip addr add 10.0.2.15/24 dev eth0
/bin/ip rule add fwmark 0x40000000/0x40000000 table 100 priority 20000
/bin/ip route add local 0.0.0.0/0 dev lo table 100
/sbin/iptables -t mangle -A PREROUTING -i eth0 -p tcp --dport 19191 -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000
/sbin/iptables -t mangle -A PREROUTING -i eth0 -p udp --dport 19191 -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000
echo 'RC21_GUEST: GUEST_RULES_FWMARK_TCP_UDP_INSTALLED'
/lab/echo &
backend=$!
/bin/rc9capwrap raw xray >/lab/xray.log 2>&1 &
xraypid=$!
ready=0
for n in $(/bin/busybox seq 1 90); do
 if /bin/busybox grep -q ':3039 ' /proc/net/tcp* 2>/dev/null; then ready=1; break; fi
 if ! /bin/busybox kill -0 "$xraypid" 2>/dev/null; then break; fi
 /bin/busybox sleep 0.1
done
if [ "$ready" != 1 ]; then
 echo 'RC21_GUEST: HARD_NO_GO_REAL_XRAY_LISTENER_NOT_READY'
 /bin/busybox cat /proc/net/tcp /proc/net/tcp6 2>/dev/null || true
 /bin/busybox cat /lab/xray.log
 exit 2
fi
uid=$(/bin/busybox awk '/^Uid:/ {print $2}' /proc/$xraypid/status)
caps=$(/bin/busybox awk '/^CapEff:/ {print $2}' /proc/$xraypid/status)
echo "RC21_GUEST: Xray process witness pid=$xraypid uid=$uid capeff=$caps"
test "$uid" = 65534
test "$caps" = 0000000000002000
# Linux 4.9 may lack NoNewPrivs in /proc/PID/status. The exact capwrap
# emits this marker ONLY after PR_SET_NO_NEW_PRIVS succeeds, before exec.
# PR_SET_NO_NEW_PRIVS survives exec. Do not infer from a missing proc field.
/bin/busybox grep -Fq 'RC9_CAP: BEFORE_EXEC target=xray raw=1 uid=65534 gid=65534 no_new_privs=1' /lab/xray.log
echo 'RC21_GUEST: REAL_XRAY_UID65534_CAP_NET_RAW_NNP_AND_TPROXY_LISTENER_READY'
wait "$backend"
/sbin/iptables -t mangle -xvnL PREROUTING >/lab/counters
/bin/busybox cat /lab/counters
/bin/busybox awk '($3=="TPROXY" && $4=="tcp" && $1+0>=1){tcp=1} ($3=="TPROXY" && $4=="udp" && $1+0>=1){udp=1} END{if(tcp&&udp)exit 0;exit 2}' /lab/counters
echo 'RC21_GUEST: REAL_XRAY_BACKEND_TCP_UDP_AND_TPROXY_COUNTERS'
/bin/busybox tail -n 45 /lab/xray.log
echo 'RC21_GUEST: HARD_NO_GO_HOST_UDP_RETURN_DIRECT_FALLBACK_PHYSICAL_BOOT_RESCUE'
