#!/bin/sh
PATH=/opt/bin:/opt/sbin:/usr/bin:/usr/sbin:/bin:/sbin

IPT=/opt/sbin/iptables
CHAIN=XRAY_KS_HOME
LOG=/opt/var/log/xray-ks-home.log

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG"
}

$IPT -n -L "$CHAIN" >/dev/null 2>&1 ||
    $IPT -N "$CHAIN" || exit 1

# Сохраняем доступ к локальным адресам
$IPT -C "$CHAIN" -d 192.168.0.0/16 \
    -j RETURN 2>/dev/null ||
    $IPT -I "$CHAIN" 1 -d 192.168.0.0/16 \
    -j RETURN || exit 1

# Запрет прямого транзита Home
$IPT -C "$CHAIN" -i br0 -s 192.168.1.0/24 \
    -j DROP 2>/dev/null ||
    $IPT -A "$CHAIN" -i br0 -s 192.168.1.0/24 \
    -j DROP || exit 1

# Проверяем первое правило FORWARD
FIRST=$($IPT -S FORWARD | sed -n '2p')

if [ "$FIRST" != "-A FORWARD -j $CHAIN" ]; then
    $IPT -I FORWARD 1 -j "$CHAIN" || exit 1
    log "FORWARD_RULE_RESTORED"
fi

exit 0
