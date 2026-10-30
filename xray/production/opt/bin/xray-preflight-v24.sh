#!/opt/bin/sh

PATH=/opt/bin:/opt/sbin:/usr/bin:/bin:/sbin
LOCK=/opt/tmp/xray-control.lock
CONFIG=/opt/etc/xray/config.json

check() {
    echo "=== PROCESS ==="

    /opt/bin/python3 /opt/bin/xray-identity-v24.py ||
        return 1

    echo "=== CONFIG ==="

    /opt/sbin/xray run -test -config "$CONFIG" \
        >/dev/null 2>&1 || return 1

    echo "CONFIG_VALID: YES"

    echo "=== SOCKS ==="

    netstat -lnt 2>/dev/null |
        grep -q '127.0.0.1:10808' ||
        return 1

    echo "SOCKS_LISTENING: YES"

    echo "=== RESULT ==="
    echo "PREFLIGHT: PASS"
    echo "XRAY_RESTARTED: NO"
    echo "CONFIG_CHANGED: NO"
}

if [ "$1" = "--locked" ]; then
    check
    exit $?
fi

/opt/bin/flock -n "$LOCK" "$0" --locked

