#!/bin/sh
PATH=/opt/bin:/opt/sbin:/usr/bin:/usr/sbin:/bin:/sbin
LOG=/opt/tmp/xray-fc-recover.log

restore_rule() {
    proto="$1"
    if ! iptables -t mangle -C PREROUTING \
        -s 192.168.1.0/24 -i br0 \
        -p "$proto" -j XRAY_WIFI 2>/dev/null
    then
        iptables -t mangle -I PREROUTING 1 \
            -s 192.168.1.0/24 -i br0 \
            -p "$proto" -j XRAY_WIFI || return 1
    fi
}

restore_rule tcp || exit 1
restore_rule udp || exit 1

while iptables -D FORWARD -j XRAY_FC_TEST 2>/dev/null; do
    :
done

iptables -F XRAY_FC_TEST 2>/dev/null
iptables -X XRAY_FC_TEST 2>/dev/null

echo "$(date) RECOVERY_OK" >> "$LOG"
