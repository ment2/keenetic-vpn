#!/bin/sh
PATH=/opt/bin:/opt/sbin:/usr/bin:/usr/sbin:/bin:/sbin

CHAIN=XRAY_KILLSWITCH

# Не изменяем существующую цепочку при повторном запуске
if iptables -n -L "$CHAIN" >/dev/null 2>&1; then
    echo "Chain already exists; inspect manually"
    exit 1
fi

iptables -N "$CHAIN" || exit 1

iptables -A "$CHAIN" \
    -d 192.168.0.0/16 -j RETURN || exit 1

iptables -A "$CHAIN" \
    -i br0 -s 192.168.1.0/24 -j DROP || exit 1

iptables -I FORWARD 1 -j "$CHAIN" || exit 1

echo "Kill switch enabled"
