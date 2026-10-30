#!/bin/sh

IPT=/opt/sbin/iptables
CHAIN=XRAY_WIFI

$IPT -t mangle -N "$CHAIN" 2>/dev/null
$IPT -t mangle -F "$CHAIN"

# Не перехватываем локальные и служебные адреса
for NET in \
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
  $IPT -t mangle -A "$CHAIN" -d "$NET" -j RETURN
done

# Перехватываем TCP и направляем в Xray
$IPT -t mangle -A "$CHAIN" -p tcp \
  -j TPROXY \
  --on-port 12345 \
  --tproxy-mark 0x40000000/0x40000000

# Подключаем цепочку только к Wi-Fi Keenetic
$IPT -t mangle -C PREROUTING \
  -i br0 -s 192.168.1.0/24 \
  -p tcp -j "$CHAIN" 2>/dev/null ||
$IPT -t mangle -I PREROUTING 1 \
  -i br0 -s 192.168.1.0/24 \
  -p tcp -j "$CHAIN"

echo "XRAY WIFI TCP ENABLED"
