#!/bin/sh
PATH=/opt/bin:/opt/sbin:/usr/bin:/usr/sbin:/bin:/sbin

CHAIN=XRAY_FC_TEST
LOG=/opt/tmp/xray-failclosed-test.log
ROLLBACK=/opt/bin/xray-failclosed-rollback.sh

TCP="-s 192.168.1.0/24 -i br0 -p tcp -j XRAY_WIFI"
UDP="-s 192.168.1.0/24 -i br0 -p udp -j XRAY_WIFI"

log() {
    echo "$(date) $1" >> "$LOG"
}

# Проверяем исходное состояние
iptables -t mangle -C PREROUTING $TCP || exit 1
iptables -t mangle -C PREROUTING $UDP || exit 1

if iptables -n -L "$CHAIN" >/dev/null 2>&1; then
    echo "Test already active"
    exit 1
fi

# Создаём восстановитель
cat > "$ROLLBACK" <<'EOF'
#!/bin/sh
PATH=/opt/bin:/opt/sbin:/usr/bin:/usr/sbin:/bin:/sbin
LOG=/opt/tmp/xray-failclosed-test.log

TCP="-s 192.168.1.0/24 -i br0 -p tcp -j XRAY_WIFI"
UDP="-s 192.168.1.0/24 -i br0 -p udp -j XRAY_WIFI"

iptables -t mangle -C PREROUTING $TCP 2>/dev/null ||
    iptables -t mangle -I PREROUTING 1 $TCP

iptables -t mangle -C PREROUTING $UDP 2>/dev/null ||
    iptables -t mangle -I PREROUTING 1 $UDP

while iptables -D FORWARD -j XRAY_FC_TEST 2>/dev/null; do :; done
iptables -F XRAY_FC_TEST 2>/dev/null
iptables -X XRAY_FC_TEST 2>/dev/null

echo "$(date) RESTORED" >> "$LOG"
EOF

chmod 700 "$ROLLBACK"

# Защита от прямого транзита
iptables -N "$CHAIN" || exit 1
iptables -A "$CHAIN" -d 192.168.0.0/16 -j RETURN
iptables -A "$CHAIN" -i br0 -s 192.168.1.0/24 -j DROP
iptables -I FORWARD 1 -j "$CHAIN" || {
    "$ROLLBACK"
    exit 1
}

# Фоновое восстановление через 30 секунд
(
    sleep 30
    "$ROLLBACK"
) </dev/null >/dev/null 2>&1 &

log "ROLLBACK_SCHEDULED"

# Временно отключаем перехват
iptables -t mangle -D PREROUTING $TCP || {
    "$ROLLBACK"
    exit 1
}

iptables -t mangle -D PREROUTING $UDP || {
    "$ROLLBACK"
    exit 1
}

log "TPROXY_DISABLED"
echo "TEST ACTIVE FOR 30 SECONDS"
