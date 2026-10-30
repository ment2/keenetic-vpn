#!/opt/bin/sh

PATH=/opt/bin:/opt/sbin:/usr/bin:/bin:/sbin
FAIL=0

check() {
    if "$@" >/dev/null 2>&1; then
        echo "PASS: $*"
    else
        echo "FAIL: $*"
        FAIL=1
    fi
}

echo "=== FORWARD KILL SWITCH ==="

check iptables -C FORWARD \
    -j XRAY_KS_HOME

check iptables -C XRAY_KS_HOME \
    -i br0 -s 192.168.1.0/24 -j DROP

echo "=== TPROXY ==="

check iptables -t mangle -C PREROUTING \
    -s 192.168.1.0/24 -i br0 \
    -p tcp -j XRAY_WIFI

check iptables -t mangle -C PREROUTING \
    -s 192.168.1.0/24 -i br0 \
    -p udp -j XRAY_WIFI

echo "=== ROUTING ==="

ip -4 rule show
ip -4 route show table 100

echo "=== IPV6 ==="

ip -6 rule show
ip -6 route show
ip6tables -S FORWARD 2>&1
ip6tables -S OUTPUT 2>&1

echo "=== RESULT ==="

if [ "$FAIL" -ne 0 ]; then
    echo "BASELINE: FAIL"
    exit 1
fi

echo "BASELINE: PASS"
echo "LEAK_PROTECTION: NOT FULLY VERIFIED"
exit 0