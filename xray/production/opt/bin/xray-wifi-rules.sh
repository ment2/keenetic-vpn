#!/bin/sh

IPT=/opt/sbin/iptables
CHAIN=XRAY_WIFI
MARK=0x40000000/0x40000000

# Таблица маршрутизации для TPROXY
ip rule show | grep -q 'fwmark 0x40000000/0x40000000 lookup 100' ||
    ip rule add fwmark "$MARK" lookup 100 priority 20000

ip route replace local default dev lo table 100

# Создать цепочку, если отсутствует
$IPT -t mangle -N "$CHAIN" 2>/dev/null

# Полностью восстановить содержимое цепочки
$IPT -t mangle -F "$CHAIN"

for net in \
    0.0.0.0/8 \
    10.0.0.0/8 \
    100.64.0.0/10 \
    127.0.0.0/8 \
    169.254.0.0/16 \
    172.16.0.0/12 \
    192.168.0.0/16 \
    224.0.0.0/4 \
    240.0.0.0/4
do
    $IPT -t mangle -A "$CHAIN" -d "$net" -j RETURN
done

for proto in tcp udp
do
    $IPT -t mangle -A "$CHAIN" -p "$proto" \
        -j TPROXY --on-port 12345 \
        --tproxy-mark "$MARK"

    $IPT -t mangle -C PREROUTING \
        -s 192.168.1.0/24 -i br0 -p "$proto" \
        -j "$CHAIN" 2>/dev/null ||
    $IPT -t mangle -I PREROUTING 1 \
        -s 192.168.1.0/24 -i br0 -p "$proto" \
        -j "$CHAIN"
done
