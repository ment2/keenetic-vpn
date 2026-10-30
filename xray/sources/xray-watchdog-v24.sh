#!/opt/bin/sh

LOG=/opt/tmp/xray-watchdog.log
SERVICE=/opt/etc/init.d/S97xray
LOCK=/opt/tmp/xray-control.lock

port_ready() {
    netstat -lnt 2>/dev/null |
        grep -q '127.0.0.1:10808'
}

recover() {
    # Recheck after acquiring the shared lock.
    if port_ready; then
        return 0
    fi

    echo "$(date) SOCKS5 unavailable; recovery needed" >> "$LOG"

    # Recovery is deliberately disabled in this candidate.
    # Never call the old service while it uses killall.
    echo "$(date) V24: recovery deferred until safe controller is ready" >> "$LOG"

    return 1
}

while :; do
    if ! port_ready; then
        /opt/bin/flock -n "$LOCK" \
            /opt/bin/sh -c '
                netstat -lnt 2>/dev/null |
                    grep -q "127.0.0.1:10808" ||
                    echo "V24: recovery required"
            '
    fi

    sleep 30
done