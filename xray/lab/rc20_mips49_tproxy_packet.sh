#!/bin/sh
# RC20: actual guest-only TPROXY redirection and counters. No external network.
set -eu
/bin/ip link set lo up
/bin/ip link set dev eth0 up
/bin/ip address add 10.0.2.15/24 dev eth0
/bin/ip rule add fwmark 0x40000000/0x40000000 table 100 priority 20000
/bin/ip route add local 0.0.0.0/0 dev lo table 100
echo 'RC20_GUEST: BEFORE_TCP_TPROXY_RULE'
/sbin/iptables -t mangle -A PREROUTING -i eth0 -p tcp --dport 19191 -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000
echo 'RC20_GUEST: TCP_TPROXY_RULE_INSTALLED'
/sbin/iptables -t mangle -A PREROUTING -i eth0 -p udp --dport 19191 -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000
echo 'RC20_GUEST: POLICY_FWMARK_AND_TCP_UDP_TPROXY_RULES_INSTALLED'
/lab/echo
/sbin/iptables -t mangle -xvnL PREROUTING > /lab/counters
cat /lab/counters
/bin/busybox awk '($3=="TPROXY" && $4=="tcp" && $1+0>=1) {tcp=1} ($3=="TPROXY" && $4=="udp" && $1+0>=1) {udp=1} END {if(tcp && udp) exit 0; exit 2}' /lab/counters
echo 'RC20_GUEST: REAL_NETFILTER_TCP_UDP_TPROXY_COUNTERS_NONZERO'
echo 'RC20_GUEST: FULL_XRAY_PACKET_PATH_UDP_RETURN_AND_NODIRECT_FALLBACK_UNPROVEN'
