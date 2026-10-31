#!/bin/sh
# Disposable real MIPS49 xt_TPROXY ingress, original destination 10.77.0.3.
set -eu
/bin/ip link set lo up
/bin/ip link set eth0 up
/bin/ip addr add 10.0.2.15/24 dev eth0
/bin/ip link set eth1 up
/bin/ip addr add 10.77.0.2/24 dev eth1
/bin/ip rule add fwmark 0x40000000/0x40000000 table 100 priority 20000
/bin/ip route add local 0.0.0.0/0 dev lo table 100
/sbin/iptables -t mangle -A PREROUTING -i eth1 -p tcp --dport 19301 -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000
/sbin/iptables -t mangle -A PREROUTING -i eth1 -p udp --dport 19301 -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000
echo 'RC29_GUEST: REAL_TPROXY_ORIGINAL_FOREIGN_DEST_10_77_0_3_RULES_INSTALLED'
/bin/rc9capwrap raw xray > /lab/xray.log 2>&1 &
xr=$!
ready=0
for n in $(/bin/busybox seq 1 240); do
 if /bin/busybox grep -q ':3039 ' /proc/net/tcp /proc/net/tcp6 2>/dev/null && \
    /bin/busybox cat /proc/net/udp /proc/net/udp6 | /bin/busybox grep -q ':3039 '; then ready=1;break;fi
 /bin/busybox kill -0 "$xr" 2>/dev/null || break
 /bin/busybox sleep 0.1
done
if [ "$ready" != 1 ]; then
 echo RC29_GUEST_HARD_NO_GO_XRAY_LISTEN_NOT_READY
 /bin/busybox cat /lab/xray.log
 exit 3
fi
uid=$(/bin/busybox awk '/^Uid:/ {print $2}' /proc/$xr/status)
caps=$(/bin/busybox awk '/^CapEff:/ {print $2}' /proc/$xr/status)
test "$uid" = 65534; test "$caps" = 0000000000002000
/bin/busybox grep -Fq 'no_new_privs=1' /lab/xray.log
echo RC29_GUEST_REAL_XRAY_CAP_NET_RAW_NNP_READY
/bin/busybox sleep 25
echo RC29_GUEST_TPROXY_COUNTERS_BEGIN
/sbin/iptables -t mangle -xvnL PREROUTING >/lab/rc29cnt
/bin/busybox cat /lab/rc29cnt
/bin/busybox awk '($3=="TPROXY" && $4=="tcp" && $1+0>=1){tcp=1} ($3=="TPROXY" && $4=="udp" && $1+0>=1){udp=1} END{exit tcp&&udp?0:2}' /lab/rc29cnt || {
 echo RC29_GUEST_HARD_NO_GO_TCP_UDP_TPROXY_MISSING;exit 4;
}
if /bin/busybox grep -Fq 'fake: socket bind: address already in use' /lab/xray.log; then
 echo RC29_GUEST_HARD_NO_GO_UDP_BIND_COLLISION
 /bin/busybox tail -n 60 /lab/xray.log
 exit 5
fi
echo RC29_GUEST_REAL_XRAY_ORIGINAL_DEST_TPROXY_COUNTERS_POSITIVE
/bin/busybox tail -n 70 /lab/xray.log
echo RC29_GUEST_HARD_NO_GO_PHYSICAL_LEGACY_FENCING_RESCUE
