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
# Wait for the exact baseline payloads before removing our OWN direct child.
# No PID-only global kill; child identity is checked while still parent-owned.
/bin/busybox sleep 5
boot=$(/bin/busybox cat /proc/sys/kernel/random/boot_id)
xticks=$(/bin/busybox awk '{print $22}' /proc/$xr/stat)
test -n "$boot"; test "$xticks" -gt 0
/sbin/iptables -t mangle -xvnL PREROUTING >/lab/counters-before
test "$boot" = "$(/bin/busybox cat /proc/sys/kernel/random/boot_id)"
test "$xticks" = "$(/bin/busybox awk '{print $22}' /proc/$xr/stat)"
/bin/busybox kill -TERM "$xr"
wait "$xr" || true
for n in $(/bin/busybox seq 1 100); do
 if ! /bin/busybox grep -q ':3039 ' /proc/net/tcp /proc/net/tcp6 2>/dev/null && \
    ! /bin/busybox cat /proc/net/udp /proc/net/udp6 | /bin/busybox grep -q ':3039 '; then break; fi
 /bin/busybox sleep 0.1
done
if /bin/busybox grep -q ':3039 ' /proc/net/udp /proc/net/udp6 2>/dev/null;then
 echo RC30_GUEST_HARD_NO_GO_XRAY_UDP_LISTENER_SURVIVED;exit 8
fi
echo "RC30_GUEST_POSTDEATH_PROBE_READY boot=$boot pid=$xr start_ticks=$xticks"
/bin/busybox sleep 10
/sbin/iptables -t mangle -xvnL PREROUTING >/lab/counters-after
for proto in tcp udp;do
 before=$(/bin/busybox awk -v p="$proto" '$3=="TPROXY" && $4==p {print $1}' /lab/counters-before)
 after=$(/bin/busybox awk -v p="$proto" '$3=="TPROXY" && $4==p {print $1}' /lab/counters-after)
 test -n "$before" && test -n "$after" && test "$after" -gt "$before" || {
  echo "RC30_GUEST_HARD_NO_GO_POSTDEATH_COUNTERS_NOT_INCREASED";exit 9;
 }
done
echo RC30_GUEST_REAL_TCP_UDP_TPROXY_POSTDEATH_COUNTERS_INCREASED
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
