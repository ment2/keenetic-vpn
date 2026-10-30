#!/bin/sh

IPT=iptables
CHAIN=XRAY_KILLSWITCH_TEST
LOG=/opt/tmp/xray-killswitch-test.log

cleanup() {
    $IPT -D FORWARD -j "$CHAIN" 2>/dev/null
    $IPT -F "$CHAIN" 2>/dev/null
    $IPT -X "$CHAIN" 2>/dev/null
    echo "$(date) KILLSWITCH REMOVED" >> "$LOG"
}

# Запрещаем повторный запуск
if $IPT -n -L "$CHAIN" >/dev/null 2>&1; then
    echo "TEST ALREADY RUNNING"
    exit 1
fi

# Создаём отдельную цепочку
$IPT -N "$CHAIN" || exit 1

# Сохраняем доступ к основной локальной сети
$IPT -A "$CHAIN" -d 192.168.0.0/24 -j RETURN || {
    cleanup
    exit 1
}

# Блокируем прямой выход через WAN
$IPT -A "$CHAIN" -i br0 -o apclii0 \
    -s 192.168.1.0/24 -j DROP || {
    cleanup
    exit 1
}

# Подключаем защиту в самое начало FORWARD
$IPT -I FORWARD 1 -j "$CHAIN" || {
    cleanup
    exit 1
}

echo "$(date) KILLSWITCH ENABLED" >> "$LOG"

# Независимый процесс отката
(
    sleep 60
    cleanup
) </dev/null >/dev/null 2>&1 &

echo "KILLSWITCH ACTIVE FOR 60 SECONDS"
echo "ROLLBACK PID: $!"
