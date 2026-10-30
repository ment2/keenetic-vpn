#!/bin/sh
PATH=/opt/bin:/opt/sbin:/usr/bin:/usr/sbin:/bin:/sbin

while iptables -D FORWARD -j XRAY_KILLSWITCH 2>/dev/null; do
    :
done

iptables -F XRAY_KILLSWITCH 2>/dev/null
iptables -X XRAY_KILLSWITCH 2>/dev/null

echo "$(date) ROLLBACK_DONE" \
    >> /opt/tmp/xray-ks-rollback.log
