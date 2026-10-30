#!/opt/bin/sh

PATH=/opt/bin:/opt/sbin:/usr/bin:/bin:/sbin

PIDFILE=/opt/var/run/xray-watchdog-v25.pid
SCRIPT=/opt/bin/xray-watchdog-v25.sh

get_pid() {
    [ -r "$PIDFILE" ] || return 1
    PID="$(cat "$PIDFILE")"

    case "$PID" in
        ''|*[!0-9]*) return 1 ;;
    esac

    [ -r "/proc/$PID/cmdline" ] || return 1

    CMD="$(tr '\000' ' ' < "/proc/$PID/cmdline")"

    case "$CMD" in
        *"$SCRIPT"*) return 0 ;;
        *) return 1 ;;
    esac
}

case "$1" in
    start)
        if get_pid; then
            echo "ALREADY_RUNNING: $PID"
            exit 0
        fi

        /opt/bin/sh "$SCRIPT" >/dev/null 2>&1 &
        NEWPID=$!
        echo "$NEWPID" > "$PIDFILE"

        echo "STARTED: $NEWPID"
        ;;

    status)
        if get_pid; then
            echo "RUNNING: $PID"
            exit 0
        fi

        echo "NOT_RUNNING"
        exit 1
        ;;

    stop)
        if ! get_pid; then
            echo "STOP_REFUSED: PID_NOT_VERIFIED"
            exit 1
        fi

        kill "$PID" || exit 1
        rm -f "$PIDFILE"
        echo "STOPPED: $PID"
        ;;

    *)
        echo "Usage: $0 start|status|stop"
        exit 2
        ;;
esac