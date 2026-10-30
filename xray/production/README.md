# Keenetic production source snapshot — 2026-10-30

This folder is a **read-only, verified snapshot** of the Keenetic Ultra production source files discovered under `/opt/bin` and `/opt/etc/init.d` for Xray/VPN and adjacent Telegram service. It is **not** a deploy script and is **not** a complete copy of the router filesystem.

## Proven parity
- **63 of 63** enumerated nonsecret source/backup files were read from the router and copied to their corresponding paths below `opt/`.
- Independent SHA256 over the GitHub file bytes matched live router `sha256sum` for **all 63 files**. See `MANIFEST.sha256`.
- Git executable modes reflect router executability: **44** `100755`, **19** `100644`. Git cannot preserve exact router permissions such as `0700` or `0600`, ownership or timestamps. Do **not** restore these files blindly without an explicit permissions and ownership plan.
- Source inventory and hashes were collected from live read-only Keenetic Mobile jobs; no router modifications were made during snapshotting.
- Historical backups are retained as separate files with their actual router names, not silently substituted for active scripts.

## Actual cron and service dependencies
Read-only inspection of `/opt/var/spool/cron/crontabs/root` found:
- Every 15 minutes: `/opt/bin/xray-safe-hourly.sh` under `flock` (stages pending config, does **not** apply/restart Xray).
- Every minute and again at +30 seconds: one-shot `/opt/telegram-ai/keenetic_agent.py` under `flock`.
- `/opt/etc/crontab` separately invokes `run-parts` directories.

Live init scripts: `S96xray-killswitch`, `S97xray`, `S98xray-wifi`, `S99xray-watchdog`. **`S99xray` is absent**. Historical `xray-auto-update.sh` and `xray-safe-v23.sh` reference missing `S99xray`, but the actual cron uses `xray-safe-hourly.sh`; watchdog uses `S97xray`.

## Explicitly excluded secrets and non-source artifacts
Never commit raw `/opt/etc/xray/config.json`, `subscription.url`, provider URLs, UUIDs, credentials, private keys, tokens, Telegram sessions, or unredacted operational logs. Raw cron is not committed; only the selected redacted schedule and its SHA256 are documented. Current generated Xray config SHA256 was recorded in `docs/production/2026-10-30-inventory.md`, but the config content remains on the router.

This snapshot does not attest to the installed Python Agent source or Cloudflare Worker binaries, whose source of truth is `ment2/keenetic-control`; it does not capture Xray binary, package versions, kernel state, firewall or runtime routes. For full disaster recovery those must be documented and separately verified.

## Audit provenance
See `docs/production/2026-10-30-source-diff.md`. Branch `snapshot/keenetic-production-2026-10-30` is separate from `main`; no deployment, merge or router changes are implied.
