#!/bin/sh
LOG=/opt/var/log/xray-update.log
RESULT=$(python3 /opt/bin/update_xray_subscription.py --apply 2>&1)
STATUS=$?
printf "%s %s\n" "$(date)" "$RESULT" >> "$LOG"
[ "$STATUS" -eq 0 ] || exit 1
case "$RESULT" in
  UPDATED:*)
    /opt/etc/init.d/S99xray stop
    /opt/etc/init.d/S99xray start
    ;;
esac
