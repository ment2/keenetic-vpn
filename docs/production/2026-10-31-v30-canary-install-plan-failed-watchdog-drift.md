# Xray v30: exact approved canary file installed; --plan FAILS CLOSED on watchdog SHA drift

Date 2026-10-31. This is a factual production preflight incident report, **NOT** authorization to execute migration.

**Scope:** `ment2/keenetic-vpn`, branch `feature/xray-v30-stable-tcp-ingress-lab-20261031`. User explicitly approved ONLY installing one immutable GitHub source file to a fixed path, chmod 0700, independent sha256sum check, and precisely one `--plan` invocation. Explicit prohibitions: no `--trial`, `--rollback`, `--guardian`, no Xray/watchdog/S98 signals, no firewall/routes/cron/kill-switch, Cloudflare/production config changes, and no merge/deploy. The following jobs respect that scope.

## Immutable source and CI evidence

- Source: `xray/staging/v30_first_cutover_canary.py`; Git blob SHA `08b172af082df1284be35f39592942c0942a377b`.
- Source SHA256 `93f187cadbe985e65e67f619f9f3d7c1c8f120cdb9a506b22419a75cdeabdb4d`, 21,363 bytes.
- GitHub workflow `41198879628` **SUCCESS**, pinned `sha256sum -c` passed and 240/240 offline tests passed; **not evidence of live rollback**. Documentation consent record: `docs/production/2026-10-31-v30-canary-install-approval-sha256.md`.
- GitHub source was freshly fetched and matched the exact approved blob SHA/byte size before the one write.

## One-time router jobs and actual results

1. **Write file** `0fef7a33-569e-4d09-bd63-7fc44f4c3cb9`: `done`, `exit_code=0`, `written=true`; target `/opt/bin/v30_first_cutover_canary.py`; server-returned SHA256 `93f187cadbe985e65e67f619f9f3d7c1c8f120cdb9a506b22419a75cdeabdb4d`, `backup_created=false`. No repeat write job.
2. **chmod and independent local hash** `07044ced-7803-43c6-a3bb-c8e68d1ec306`: `done`, `exit_code=0`. Exact action: `chmod 0700 /opt/bin/v30_first_cutover_canary.py`, `sha256sum`, `test` equality with pinned SHA, `ls -l`. Output: `-rwx------ 1 root root 21363 ... /opt/bin/v30_first_cutover_canary.py`, `XRAY_V30_INSTALL_SHA_AND_MODE_OK`.
3. **Only approved --plan** `d1e4f373-fd2e-4afd-994e-a5f5b137af0d`: `done`, `exit_code=1`. The exact approved invocation:
```sh
/opt/bin/python3 /opt/bin/v30_first_cutover_canary.py --plan --expected-old-pid 13546 --expected-old-ticks 100216734 --expected-config-sha 66d074f32fffbf4a251576c8297714e9647174546e9e73e5bf27cf2768efe6d7
```
Result:
```text
Traceback (most recent call last):
  File "/opt/bin/v30_first_cutover_canary.py", line 191, in preflight
    verify_backup()
  File "/opt/bin/v30_first_cutover_canary.py", line 177, in verify_backup
    raise GateError("supervisor/source drift detected: " + Path(path).name)
GateError: supervisor/source drift detected: xray-watchdog.sh
```
No `READ_ONLY_PRECHECK_OK` returned. This is **expected fail-closed behavior** when supervisor code no longer matches pinned provenance.

## Meaning and limits

- Current working `/opt/bin/xray-watchdog.sh` does **not** have the SHA256 hard-coded in the installed canary: `dddcc1d324e30b91df041378645ada869a18b4d35f2842383e5d319fc859e08`. The present *actual* file SHA256 was not returned by this exception; the reason for drift has **not** been established. Earlier read-only snapshot 2026-10-31 ~11:20 UTC showed the original expected SHA; thus something changed or the file identity diverged between snapshots. It could be an authorized automatic process or another cause: do not assume.
- `verify_backup()` checks the backup manifest, 11 backed-up file hashes, active config/binary, then pinned init and watchdog script SHA. The watchdog mismatch aborts **before** further `safe_kernel()` and watcher identity checks. We cannot infer their current post-drift values from this failed plan.
- The program file is now installed and readable/executable for root. **No service/control action** was invoked from its `--trial`, `--rollback` or `--guardian` paths. No Python guardian, migration journal, candidate config or listeners were intentionally created by `--plan`.
- No repeat write, chmod, or plan job was enqueued. The next action cannot be an automatic rewrite of expected WD_SHA, disabling watchdog, stopping services, or rerunning --plan without new approval.
- Existing root-only backup `/opt/var/backups/xray-v30-precutover-20261031-1045Z` was not overwritten.
- This turn did not update Cloudflare, production Xray configuration, firewall, routes, cron, kill-switch, GitHub main or snapshot, and did not perform merge/deploy.

## Correct next gate (requires a fresh, restricted approval)

**CUTOVER BLOCKED.** Request a separate **read-only** diagnostic of `sha256sum /opt/bin/xray-watchdog.sh`, mode/mtime and a diff against the locally preserved copy (redact secrets if present). Determine whether a legitimate automatic updater/agent changed the file and whether that change is allowed. Do not print full private configuration or tokens. Reconcile source provenance and update candidate source + tests **only in this feature branch** if the newer script is reviewed and safe; obtain fresh installation approval for **new** full content/SHA, not silent in-place patch. No `--trial` until independently tested real rollback and explicit exact-operation approval.

**Disposition:** install succeeded, read-only plan failed closed. Work stops before any cutover.
