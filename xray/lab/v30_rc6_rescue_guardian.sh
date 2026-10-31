#!/bin/sh
# RC6 DISPOSABLE REHEARSAL ONLY. Run with host /bin/sh and sha256sum,
# not Python, Xray, Entware, /opt, cron, iptables or router boot hooks.
set -eu
umask 077
if [ "$#" -ne 2 ]; then
  echo "RC6: usage: guardian.sh <absolute-review-source> <absolute-disposable-target>" >&2
  exit 64
fi
SRC=$1
DST=$2
case "$SRC:$DST" in
  /tmp/*:/tmp/*|/home/runner/work/*:/home/runner/work/*) ;;
  *) echo "RC6: refusing non-disposable path" >&2; exit 65 ;;
esac
if [ -L "$SRC" ] || [ -L "$SRC/originals" ] || [ -L "$DST" ]; then
  echo "RC6: symlink denied" >&2
  exit 66
fi
if [ ! -d "$SRC/originals" ] || [ ! -f "$SRC/SHA256SUMS" ] || [ ! -d "$DST" ]; then
  echo "RC6: missing exact standalone source/target" >&2
  exit 67
fi
for name in S97 S98 S99 watchdog wifi_rules; do
  if [ -L "$SRC/originals/$name.sh" ] || [ ! -f "$SRC/originals/$name.sh" ]; then
    echo "RC6: untrusted recovery file" >&2
    exit 68
  fi
  if [ -L "$DST/$name.sh" ]; then
    echo "RC6: destination symlink denied" >&2
    exit 69
  fi
done
# Refuse corrupt/missing *any* source BEFORE writing *any* target.
(cd "$SRC" && sha256sum -c SHA256SUMS >/dev/null 2>&1) || {
  echo "RC6: source SHA mismatch; ZERO recovery writes" >&2
  exit 70
}
n=0
for name in S97 S98 S99 watchdog wifi_rules; do
  tmp="$DST/.$name.sh.rc6.$$"
  if [ -e "$tmp" ] || [ -L "$tmp" ]; then
    echo "RC6: temp collision" >&2
    exit 71
  fi
  cp "$SRC/originals/$name.sh" "$tmp"
  chmod 600 "$tmp"
  cmp -s "$SRC/originals/$name.sh" "$tmp" || {
    rm -f "$tmp"
    echo "RC6: copy failed" >&2
    exit 72
  }
  mv "$tmp" "$DST/$name.sh"
  n=$((n+1))
  if [ "${V30_RC6_FAULT:-}" = "after-2" ] && [ "$n" -eq 2 ]; then
    echo "RC6: injected process death after exactly two replacements"
    exit 75
  fi
done
for name in S97 S98 S99 watchdog wifi_rules; do
  cmp -s "$SRC/originals/$name.sh" "$DST/$name.sh" || {
    echo "RC6: post-restore mismatch" >&2
    exit 76
  }
done
echo "RC6_SH: PASS five originals checked and restored with host /bin/sh and sha256sum"
echo "RC6_SH: LIMITATION not physically durable, no boot guardian installed"
