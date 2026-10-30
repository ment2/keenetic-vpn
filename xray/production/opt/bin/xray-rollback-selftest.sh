#!/bin/sh
PATH=/opt/bin:/opt/sbin:/usr/bin:/usr/sbin:/bin:/sbin
LOG=/opt/tmp/xray-rollback-selftest.log

echo "$(date) STARTED" >> "$LOG"

(
    sleep 30
    echo "$(date) TIMER_EXECUTED" >> "$LOG"
) </dev/null >/dev/null 2>&1 &

echo "Rollback timer scheduled"
