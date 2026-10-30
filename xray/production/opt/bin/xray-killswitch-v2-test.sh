#!/bin/sh

CHAIN=XRAY_KS_V2
LOG=/opt/tmp/xray-killswitch-v2.log

cleanup() {
    while iptables -D FORWARD -j "$CHAIN" 2>/dev/null; do
        :
    done
    iptables -F "$CHAIN" 2>/dev/null
    iptables -X "$CHAIN" 2>/dev/null
    echo "$(date) REMOVED" >> "$LOG"
}

if iptables -n -L "$CHAIN" >/dev/null 2>&1; then
    echo "CHAIN ALREADY EXISTS"
    exit 1
fi

iptables -N "$CHAIN" || exit 1

# Локальные адреса оставляем штатной маршрутизации Keenetic
iptables -A "$CHAIN" -d 192.168.0.0/16 -j RETURN || {
    cleanup
    exit 1
}

# Прямой транзит из домашней сети запрещаем
iptables -A "$CHAIN" -i br0 \
    -s 192.168.1.0/24 -j DROP || {
    cleanup
    exit 1
}

# В начало FORWARD, до разрешения ESTABLISHED
iptables -I FORWARD 1 -j "$CHAIN" || {
    cleanup
    exit 1
}

echo "$(date) ENABLED" >> "$LOG"

(
    sleep 120
    cleanup
) </dev/null >/dev/null 2>&1 &

echo "KILLSWITCH ACTIVE: 120 SECONDS"
echo "ROLLBACK PID: $!"
