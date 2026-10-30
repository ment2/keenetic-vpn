#!/opt/bin/sh

PATH=/opt/bin:/opt/sbin:/usr/bin:/bin:/sbin

echo "=== MAIN XRAY ==="
/opt/bin/python3 /opt/bin/xray-main-pid.py

echo "=== WATCHDOG PROCESSES ==="
ps w | grep '[x]ray-watchdog'

echo "=== WATCHDOG PID FILES ==="

for file in \
    /opt/var/run/xray-watchdog.pid \
    /opt/var/run/xray-watchdog-v25.pid
do
    if [ -f "$file" ]; then
        echo "PIDFILE: $file"
        cat "$file"
        echo
    else
        echo "ABSENT: $file"
    fi
done

echo "=== STARTUP SERVICES ==="
ls -l \
    /opt/etc/init.d/S99xray-watchdog \
    /opt/etc/init.d/S96xray-killswitch

echo "=== LISTENERS ==="
netstat -lnt 2>/dev/null |
    grep -E '10808|12345'

echo "=== AUDIT COMPLETE ==="
echo "NO_CHANGES_MADE"