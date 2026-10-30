#!/opt/bin/sh

PATH=/opt/bin:/opt/sbin:/usr/bin:/bin:/sbin

PIDFILE=/opt/var/run/xray-watchdog-v25.pid
SCRIPT=/opt/bin/xray-watchdog-v25.sh

case "$1" in
    start)
        if [ -f "$PIDFILE" ]; then
            PID="$(cat "$PIDFILE")"
            if kill -0 "$PID" 2>/dev/null; then
                echo "Already running: $PID"
                exit 0
            fi
        fi

        /opt/bin/sh "$SCRIPT" \
            >/dev/null 2>&1 &

        echo $! > "$PIDFILE"
        echo "Started v25 watchdog"
        ;;

    status)
        if [ -f "$PIDFILE" ]; then
            PID="$(cat "$PIDFILE")"
            if kill -0 "$PID" 2>/dev/null; then
                echo "RUNNING: $PID"
                exit 0
            fi
        fi

        echo "NOT_RUNNING"
        exit 1
        ;;

    stop)
        echo "STOP_DISABLED_PENDING_MIGRATION"
        exit 1
        ;;

    *)
        echo "Usage: $0 start|status"
        exit 2
        ;;
esac