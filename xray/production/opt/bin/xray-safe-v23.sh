#!/bin/sh
set -u
PATH=/opt/bin:/opt/sbin:/usr/bin:/usr/sbin:/bin:/sbin
LOG=/opt/var/log/xray-update.log
CONF=/opt/etc/xray/config.json
BACKUP=/opt/etc/xray/config.lastgood.json
SERVICE=/opt/etc/init.d/S99xray
UPDATER=/opt/bin/xray-update-v23.py
XRAY=/opt/sbin/xray

log() {
    printf '%s %s\n' "$(date '+%F %T')" "$1" >> "$LOG"
}

probe() {
    pidof xray >/dev/null 2>&1 || return 1
    code=$(/opt/bin/curl --silent --show-error \
        --connect-timeout 8 --max-time 20 \
        --socks5-hostname 127.0.0.1:10808 \
        -o /dev/null -w '%{http_code}' \
        https://api.openai.com/v1/models 2>/dev/null) || return 1
    [ "$code" = 401 ] || [ "$code" = 200 ]
}

healthy() {
    i=0
    while [ "$i" -lt 3 ]; do
        probe && return 0
        i=$((i + 1))
        sleep 3
    done
    return 1
}

mkdir -p /opt/var/log
WORK=$(mktemp -d /opt/etc/xray/.update.XXXXXX) || exit 1
trap 'rm -rf "$WORK"' 0
trap 'exit 1' 1 2 3 15

CANDIDATE="$WORK/candidate.json"
PREVIOUS="$WORK/previous.json"
STAGED="$WORK/staged.json"

if ! /opt/bin/python3 "$UPDATER" --output "$CANDIDATE" \
    >> "$LOG" 2>&1; then
    log 'SKIP: candidate validation failed'
    exit 1
fi

[ -s "$CANDIDATE" ] || {
    log 'SKIP: empty candidate'
    exit 1
}

"$XRAY" run -test -config "$CANDIDATE" \
    >> "$LOG" 2>&1 || exit 1

if cmp -s "$CANDIDATE" "$CONF"; then
    log 'UNCHANGED: no restart'
    exit 0
fi

cp -p "$CONF" "$PREVIOUS" || exit 1
cp -p "$PREVIOUS" "$BACKUP" || exit 1
cp -p "$CANDIDATE" "$STAGED" || exit 1

mv -f "$STAGED" "$CONF" || exit 1

"$SERVICE" stop >> "$LOG" 2>&1
sleep 2
"$SERVICE" start >> "$LOG" 2>&1

if healthy; then
    log 'SUCCESS: OpenAI VPN pool active'
    exit 0
fi

log 'ERROR: rolling back'
cp -p "$PREVIOUS" "$WORK/restore.json" || exit 1
mv -f "$WORK/restore.json" "$CONF" || exit 1

"$SERVICE" stop >> "$LOG" 2>&1
sleep 2
"$SERVICE" start >> "$LOG" 2>&1

if healthy; then
    log 'ROLLBACK_OK'
else
    log 'CRITICAL: rollback health check failed'
fi
exit 1
