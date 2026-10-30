#!/opt/bin/sh

PATH=/opt/bin:/opt/sbin:/usr/bin:/bin:/sbin
FAIL=0

check_file() {
    if [ -f "$1" ] && [ -r "$1" ]; then
        echo "FILE_OK: $1"
    else
        echo "FILE_FAIL: $1"
        FAIL=1
    fi
}

echo "=== V25 FILES ==="
check_file /opt/bin/xray-watchdog-v25.sh
check_file /opt/bin/xray-failclosed-audit-v25.sh
check_file /opt/etc/init.d/S99xray-watchdog
check_file /opt/etc/init.d/S96xray-killswitch

echo "=== MAIN XRAY ==="
/opt/bin/python3 /opt/bin/xray-identity-v24.py ||
    FAIL=1

echo "=== CURRENT WATCHDOG ==="
ps w | grep '[x]ray-watchdog'

echo "=== SOCKETS ==="
netstat -lnt 2>/dev/null |
    grep -E '10808|12345'

echo "=== RESULT ==="
if [ "$FAIL" -ne 0 ]; then
    echo "MIGRATION_PREFLIGHT: FAIL"
    exit 1
fi

echo "MIGRATION_PREFLIGHT: PASS"
echo "CONFIG_CHANGED: NO"
echo "PROCESS_CHANGED: NO"