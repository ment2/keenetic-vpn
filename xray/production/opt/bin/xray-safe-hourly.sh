#!/opt/bin/sh
set -eu
PATH=/opt/bin:/opt/sbin:/usr/bin:/usr/sbin:/bin:/sbin
LOG=/opt/var/log/xray-update.log
CONF=/opt/etc/xray/config.json
PENDING=/opt/etc/xray/config.pending.json
UPDATER=/opt/bin/xray-update-v23.py
XRAY=/opt/sbin/xray
log() { printf '%s %s\n' "$(date '+%F %T')" "$1" >> "$LOG"; }
umask 077
mkdir -p /opt/var/log
WORK=$(mktemp -d /opt/etc/xray/.update.XXXXXX) || exit 1
trap 'rm -rf "$WORK"' EXIT
trap 'exit 1' HUP INT TERM
CANDIDATE="$WORK/candidate.json"
if ! /opt/bin/python3 "$UPDATER" --output "$CANDIDATE" >> "$LOG" 2>&1; then
    log 'SKIP: OpenAI-qualified candidate generation failed; active Xray unchanged'
    exit 1
fi
if [ ! -s "$CANDIDATE" ]; then
    log 'SKIP: candidate empty; active Xray unchanged'
    exit 1
fi
if ! "$XRAY" run -test -config "$CANDIDATE" >> "$LOG" 2>&1; then
    log 'SKIP: candidate invalid; active Xray unchanged'
    exit 1
fi
if cmp -s "$CANDIDATE" "$CONF"; then
    rm -f "$PENDING"
    log 'UNCHANGED: candidate matches disk configuration; active process not reloaded'
    exit 0
fi
if cmp -s "$CANDIDATE" "$PENDING"; then
    log 'PENDING_UNCHANGED: verified candidate staged; NOT applied'
    exit 0
fi
cp "$CANDIDATE" "$WORK/staged.json"
chmod 600 "$WORK/staged.json"
mv -f "$WORK/staged.json" "$PENDING"
log 'STAGED_ONLY: OpenAI-qualified candidate validated and saved to config.pending.json; NOT applied, no restart'
exit 0
