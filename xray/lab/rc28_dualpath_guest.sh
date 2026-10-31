#!/bin/sh
set -eu
/bin/ip link set lo up
/bin/ip link set eth0 up
/bin/ip addr add 10.0.2.15/24 dev eth0
/bin/ip link set eth1 up
/bin/ip addr add 10.77.0.2/24 dev eth1
echo 'RC28_GUEST: DUAL_PCNET_NO_DEFAULT_ROUTE'
/lab/echo
echo 'RC28_GUEST: ECHO_COMPLETE'
