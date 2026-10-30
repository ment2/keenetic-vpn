#!/bin/sh
[ -f /opt/tmp/xray-fc-guard-enabled ] || exit 0
/opt/bin/xray-fc-recover.sh \
    >> /opt/tmp/xray-fc-cron-guard.log 2>&1
