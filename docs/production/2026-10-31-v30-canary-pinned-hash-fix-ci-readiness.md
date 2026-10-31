# Keenetic Xray v30 — corrected canary provenance, offline contract and next approval gate

Date: **2026-10-31**. Only `ment2/keenetic-vpn`, branch `feature/xray-v30-stable-tcp-ingress-lab-20261031`. No merge, production deploy, on-router overwrite, service or firewall changes authorized in this stage.

## Resolved incident from real Keenetic

Previously, the user explicitly approved installation of a *different exact source hash*, which was written as `/opt/bin/v30_first_cutover_canary.py` root-only mode 0700. Its one permitted `--plan` invocation failed before any cutover with `GateError: supervisor/source drift detected: xray-watchdog.sh`.

The read-only router comparison job `fdf51310-f08e-488e-b2a4-fd510ec13081` (done, exit code 0) showed **identical actual and backed-up watchdog bytes** (649 bytes, 28 lines, 0 difference hunks), SHA256 `dddfcc1d324e30b91df041378645ada869a18b4d35f2842383e5d319fc859e08`. Original canary source accidentally pinned a 63-character value `dddcc1d...`. Production watchdog is **not** shown to have changed since backup.

## Changes limited to GitHub feature branch

1. `xray/staging/v30_first_cutover_canary.py`: corrected `WD_SHA` to the verified full 64-character value. Added `validate_pinned_hashes()` covering **all eight static pins** (`BACKUP_MANIFEST_SHA`, `BIN_SHA`, `BASE_SHA`, `S97_SHA`, `S98_SHA` alias for `WIFI_SHA`, `S99_SHA`, `WD_SHA`, and `WIFI_RULES_SHA`). It rejects malformed length/non-hex/uppercase/non-string before reading any live backup file. The active binary/config/backup hash content comparisons remain required by `verify_backup()`; static syntax validation alone never authorizes a real cutover.
2. `tests/test_xray_v30_pinned_sha_contract.py`: **13** additional offline unit tests, including malformed hashes for each of 8 pins, equality of the five pinned active shell/init sources with `xray/production/MANIFEST.sha256`, SHA256 of frozen `xray-watchdog.sh` content, pin against measured 2026-10-31 live and backup, and no live-router I/O on malformed pin.
3. `.github/workflows/xray-snapshot-contracts.yml`: updated exact canary SHA256 content pin; the CI runner executes `sha256sum -c` on full source bytes. Never runs `--trial`/`--rollback` or connects to the router.

### Immutable corrected version

- GitHub source: https://github.com/ment2/keenetic-vpn/blob/feature/xray-v30-stable-tcp-ingress-lab-20261031/xray/staging/v30_first_cutover_canary.py
- **Corrected Git blob SHA:** `495cd51581f472a9cb0a257ff7cd9f0d611dcab7`.
- **Corrected UTF-8 file SHA256:** `8e57ef5054f53174a35d906d34eab073dd6d787607cb02f29d83364ae3abc203`.
- **Corrected size:** 22,208 bytes; trailing newline retained.
- For comparison, **old already-installed file** SHA256 was `93f187cadbe985e65e67f619f9f3d7c1c8f120cdb9a506b22419a75cdeabdb4d` and Git blob SHA `08b172af082df1284be35f39592942c0942a377b`. This old file **remains on Keenetic** until approved replacement.

### CI authoritative results

- **[GitHub Actions 41200967162](https://github.com/ment2/keenetic-vpn/actions/runs/41200967162) — SUCCESS**, **253/253 offline tests**, runner `xray/staging/v30_first_cutover_canary.py: OK` from `sha256sum -c`, frozen snapshot 63/63 verified, and synthetic detached-guardian `restored` and `blocked` scenarios passed.
- Prior transient CI `41200904722` failed because regression-test names used `WIFI_SHA` whereas the diagnostic map labels the underlying variable `S98_SHA`. Fixed test alias; source SHA did not change in that correction. The earlier SHA-only workflow failures (before updating source hash pin) were expected interim red builds and did not affect production.
- CI verifies **only GitHub/offline source and models**, not real Keenetic PID signals, TPROXY full TCP/UDP, IPv6/DNS leak prevention, reboot recovery or guardian survival on router.

## Exact next separate consent required

This stage **does not authorize** another router job. To proceed with source replacement, owner must separately approve writing the **new complete, specific file contents** from corrected Git blob `495cd51581f472a9cb0a257ff7cd9f0d611dcab7` to `/opt/bin/v30_first_cutover_canary.py`, chmod 0700 and independent on-device `sha256sum` against `8e57ef5054f53174a35d906d34eab073dd6d787607cb02f29d83364ae3abc203`.

Only after a successful write and exact hash validation and **explicit approval of the exact read-only command** could one `--plan` be considered:

```sh
/opt/bin/python3 /opt/bin/v30_first_cutover_canary.py --plan --expected-old-pid 13546 --expected-old-ticks 100216734 --expected-config-sha 66d074f32fffbf4a251576c8297714e9647174546e9e73e5bf27cf2768efe6d7
```

Expected PID/start-ticks values are **stale baseline identifiers**, and the script must fail closed rather than adapting silently if anything changed. No plans to run it under the current scope.

Even after an eventual passing `--plan`, **no `--trial`, `--rollback`, `--guardian`, process signals, firewall/route/cron, kill-switch, Cloudflare mutation, GitHub main/snapshot change, deploy or merge** is permitted without separate, exact approval.

## Remaining risk independent of this fixed typo

First ingress migration can still interrupt client sessions. The one detached guardian and PID-scoped signals have not been proved against real Keenetic's S97 `killall` race, S98 child processes, router reboot and USB loss. A candidate started before its PID/start-ticks are durably journaled could cause an unknown-Xray fail-closed rollback block. SOCKS 401/netstat is not end-to-end TPROXY UDP, DNS/IPv6 no-leak verification. Do not represent the canary as deployment-ready.

**Disposition:** GitHub feature candidate corrected and CI green. Router unchanged this turn, old installed canary remains. **Waiting solely on fresh exact-operation approval for source replacement.**
