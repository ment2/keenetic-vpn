#!/bin/sh
# Guest-side disposable NIC setup: no TPROXY or interception claims.
set -eu
/bin/ip link set lo up
/bin/ip link show
/bin/ip link set dev eth0 up
/bin/ip address add 10.0.2.15/24 dev eth0
echo 'RC19_GUEST: MIPS49_PCNET_NIC_CONFIGURED'
/lab/echo
echo 'RC19_GUEST: TCP_UDP_REAL_NIC_EXCHANGE_COMPLETE'
