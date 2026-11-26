#!/opt/bin/sh
set -eu
PATH=/opt/bin:/opt/sbin:/usr/bin:/usr/sbin:/bin:/sbin

LOG=/opt/var/log/xray-update.log
CONF=/opt/etc/xray/config.json
PENDING=/opt/etc/xray/config.pending.json
BACKUP=/opt/etc/xray/config.lastgood.autoapply.json
UPDATER=/opt/bin/xray-update-v23.py
XRAY=/opt/sbin/xray
SERVICE=/opt/etc/init.d/S97xray

log() {
    printf '%s %s\n' "$(date '+%F %T')" "$1" >> "$LOG"
}

probe() {
    code=$(/opt/bin/curl -q -sS --noproxy '' --max-time 15 --socks5-hostname 127.0.0.1:10808 -o /dev/null -w '%{http_code}' https://www.gstatic.com/generate_204 2>/dev/null) || return 1
    [ "$code" = 204 ] || return 1

    code=$(/opt/bin/curl -q -sS --noproxy '' --max-time 15 --socks5-hostname 127.0.0.1:10808 -o /dev/null -w '%{http_code}' https://api.openai.com/v1/models 2>/dev/null) || return 1
    [ "$code" = 401 ]
}

wait_health() {
    for attempt in 1 2 3; do
        if probe; then
            return 0
        fi
        sleep 3
    done
    return 1
}

rollback() {
    log 'ROLLBACK: restoring previous configuration'
    if cp -p "$BACKUP" "$WORK/restore.json" &&
       mv -f "$WORK/restore.json" "$CONF" &&
       "$SERVICE" restart >> "$LOG" 2>&1 &&
       wait_health; then
        log 'ROLLBACK_OK: previous pool restored'
        return 0
    fi
    log 'CRITICAL: rollback failed or VPN unhealthy'
    return 1
}

cleanup() {
    rc=$?
    trap - EXIT HUP INT TERM
    if [ "$APPLYING" = 1 ]; then
        rollback || rc=1
    fi
    rm -rf "$WORK"
    exit "$rc"
}

umask 077
mkdir -p /opt/var/log
WORK=$(mktemp -d /opt/etc/xray/.update.XXXXXX) || exit 1
APPLYING=0
trap cleanup EXIT
trap 'exit 1' HUP INT TERM

CANDIDATE="$WORK/candidate.json"

if ! /opt/bin/python3 "$UPDATER" --output "$CANDIDATE" >> "$LOG" 2>&1; then
    log 'SKIP: candidate generation failed'
    exit 1
fi

if [ ! -s "$CANDIDATE" ]; then
    log 'SKIP: candidate empty'
    exit 1
fi

if ! /opt/bin/python3 -c 'import json,sys; c=json.load(open(sys.argv[1])); sys.exit(0 if any(x.get("protocol")=="vless" for x in c["outbounds"]) else 1)' "$CANDIDATE"; then
    log 'SKIP: no VLESS servers'
    exit 1
fi

if ! "$XRAY" run -test -config "$CANDIDATE" >> "$LOG" 2>&1; then
    log 'SKIP: candidate invalid'
    exit 1
fi

if cmp -s "$CANDIDATE" "$CONF"; then
    rm -f "$PENDING"
    log 'UNCHANGED: no restart'
    exit 0
fi

cp "$CANDIDATE" "$WORK/staged.json"
chmod 600 "$WORK/staged.json"
mv -f "$WORK/staged.json" "$PENDING"

if [ ! -s "$CONF" ]; then
    log 'SKIP: active configuration missing'
    exit 1
fi

if ! "$XRAY" run -test -config "$CONF" >> "$LOG" 2>&1; then
    log 'SKIP: rollback configuration invalid'
    exit 1
fi

cp -p "$CONF" "$WORK/backup.json"
chmod 600 "$WORK/backup.json"
cmp -s "$CONF" "$WORK/backup.json"
mv -f "$WORK/backup.json" "$BACKUP"

cp "$CANDIDATE" "$WORK/apply.json"
chmod 600 "$WORK/apply.json"

APPLYING=1
mv -f "$WORK/apply.json" "$CONF"
log 'APPLY: restarting Xray with new pool'

if "$SERVICE" restart >> "$LOG" 2>&1 && wait_health; then
    APPLYING=0
    rm -f "$PENDING"
    log 'SUCCESS: new pool active; internet and OpenAI verified'
    exit 0
fi

log 'ERROR: new pool failed health checks'
exit 1
