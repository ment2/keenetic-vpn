# Production-to-GitHub source comparison — 2026-10-30

## Read-only inventory result
Keenetic job `aff33140-4c03-4120-94a3-118171453537` completed successfully, exit code 0. Production includes Xray updater, watchdog, Wi-Fi rules, kill-switch services and scripts, cron guards, rollback/self-test scripts, and historical backups. The active Xray process is documented in `2026-10-30-inventory.md`.

## Direct content comparisons
| Router source | GitHub archival source | Result |
|---|---|---|
| `/opt/bin/update_xray_subscription.py` | `xray/sources/update_xray_subscription.py.readback-2026-10-30` | Same content except router has final newline |
| `/opt/bin/xray_server_check.py` | `xray/sources/xray_server_check.py.readback-2026-10-30` | Same content except router has final newline |
| `/opt/bin/setup_xray.py` | `xray/sources/setup_xray.py.readback-2026-10-30` | Same content except router has final newline |
| `/opt/bin/xray-update-v23.py` | `xray/sources/xray-update-v23.py.readback-2026-10-30` | **Different content and size**: router 6443 chars vs archive 6006 chars |
| `/opt/bin/xray-safe-hourly.sh` | `xray/sources/xray-safe-hourly.sh.readback-2026-10-30` | **Different content**: shell escape sequence differs (around logging function) |

These comparisons used the bounded Keenetic Mobile read_file tool and GitHub fetch_file. Returned router source was not truncated. The two differing production files have been copied as independent snapshots to:
- `xray/production/opt/bin/xray-update-v23.py`
- `xray/production/opt/bin/xray-safe-hourly.sh`

**Do not replace archival files with production snapshots.** Archive provenance is preserved, and `xray/production/` is a separate working-state snapshot.

## Missing from historical archive
The production inventory identifies Wi-Fi, kill-switch, fail-closed, cron guard, rollback and self-test files beyond the 60-file Library archive. Additional read-only retrieval is queued for eight selected production files; collect and validate results before claiming the snapshot complete.

## Credentials
`/opt/etc/xray/subscription.url` is deliberately excluded. Raw `/opt/etc/xray/config.json` is deliberately excluded; its SHA256 is recorded in the inventory. Do not commit live subscription credentials or raw generated Xray configs.

## Limitations
- File content comparisons here are exact strings, not locally computed SHA256 of both copies. The production SHA256 values are in the inventory.
- Full production file inventory and runtime/cron behavior remain to be confirmed.
- No production changes were made.

## Additional captured production-only files
Eight further read-only jobs completed successfully and their returned, non-truncated, nonsecret source text was committed to `xray/production/`:
- `opt/bin/xray-ks-home-watch.sh`
- `opt/bin/xray-ks-home.sh`
- `opt/bin/xray-wifi-rules.sh`
- `opt/bin/xray-auto-update.sh`
- `opt/etc/init.d/S96xray-killswitch`
- `opt/etc/init.d/S98xray-wifi`
- `opt/bin/xray-fc-cron-guard.sh`
- `opt/bin/xray-safe-v23.sh`

Total additional captured production snapshots in this audit: **10** (including the differing v23 updater and hourly script). These were stored separately from the historical Library archive. A heuristic credential scan was applied before committing, but this is not a comprehensive secret audit.

## Remaining coverage
The production inventory also lists additional scripts, backups and self-tests. These have **not all been copied or compared**. A production-identical GitHub working tree is therefore **not yet proven**. In particular, a full review of cron contents, generated configuration redaction, installed source selection, and all runtime dependencies is still required.

## Pending read-only follow-up jobs (do not resubmit)
- `da2d6c64-d60d-4cc5-bd67-66b8b3a16908` — xray-watchdog-migrate-v25.sh
- `d43456d4-bc38-4395-a4f8-d3eac829f1e0` — xray-fc-recover.sh
- `6879a9e5-e0d9-4f44-ad62-d5ab11966664` — xray-killswitch-enable.sh
- `73ed5129-8ae3-45d6-b78c-2c626f6944d5` — xray-main-pid.py
- `0954bd27-036f-4ff8-8421-0db17c519a56` — xray-preflight-v24.sh
- `e3d2d5c7-6482-40ff-aeb0-7e9310b6eed7` — xray-control-selftest.py
- `afd9efa1-a40d-4441-bc67-c82442ef736c` — xray-rollback-selftest.sh
- `2a5427da-9d58-48f4-9806-72013d411886` — xray-killswitch-test.sh
- `73553c5a-5253-455b-a760-5a8c6ea21e59` — redacted cron inspection and checksums

Retrieve existing results through `get_router_task_result`, validate and capture only safe nonsecret content. All were queued when this note was written.
