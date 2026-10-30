#!/opt/bin/sh

PATH=/opt/bin:/opt/sbin:/usr/bin:/bin:/sbin
LOG=/opt/tmp/xray-watchdog-v25.log
INTERVAL=30

check() {
    /opt/bin/python3 \
        /opt/bin/xray-control-v24.py status \
        >/dev/null 2>&1 || return 1

    netstat -lnt 2>/dev/null |
        grep -q '127.0.0.1:10808' || return 1

    return 0
}

LAST=""

while :; do
    if check; then
        STATE="OK"
    else
        STATE="FAILED"
    fi

    if [ "$STATE" != "$LAST" ]; then
        echo "$(date) XRAY_STATE=$STATE" >> "$LOG"
        LAST="$STATE"
    fi

    sleep "$INTERVAL"
done