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

## Follow-up poll and static dependency review
All nine saved jobs were queried again without resubmission. At the latest poll, `da2d6c64-d60d-4cc5-bd67-66b8b3a16908` was **running** and the other eight were **queued**. No new read_file contents or cron output were available; no additional files were committed. These statuses must not be interpreted as successful completion.

Static analysis of the ten already captured production snapshots identified:
- `xray-ks-home-watch.sh` calls `xray-ks-home.sh` every 15 seconds. Its init service is `S96xray-killswitch`.
- `S98xray-wifi` invokes `xray-wifi-rules.sh` on a 60-second loop; that script manages `ip rule` and iptables. Both are active network-policy dependencies, not optional archival extras.
- `xray-fc-cron-guard.sh` checks the presence of `/opt/tmp/xray-fc-guard-enabled` before invoking `/opt/bin/xray-fc-recover.sh`. The recovery script is among the queued reads.
- `xray-safe-v23.sh` refers to `/opt/etc/init.d/S99xray`, while the live inventory confirmed `S97xray` and a running Xray process. **Potential service-name mismatch**; do not assume this historical wrapper is the active production updater or run it before checking the actual service path.
- `xray-auto-update.sh` also invokes `/opt/etc/init.d/S99xray`; the same service-name concern applies.
- A `127.0.0.1` SOCKS port or running process does not prove upstream VPN, Telegram or OpenAI reachability.

**Hash validation scope:** production SHA256 was captured for 11 primary paths. Exact SHA256 equivalence between all GitHub production snapshots and live files has **not** yet been computed/verified. Existing string comparisons were recorded separately. Avoid a false 'hashes match' claim.

**No production modification** was performed.

## Repeated queue audit (same nine IDs, no resubmission)
- Re-read this report and queried all nine existing Keenetic jobs again.
- Job `da2d6c64-d60d-4cc5-bd67-66b8b3a16908` remains **running** with the same reported lease deadline `1793392309114` (epoch milliseconds); all eight subsequent jobs remain **queued**. This persistent state may indicate delayed or stalled agent processing; **not enough evidence yet** to diagnose the cause.
- The permission endpoint independently confirms `remote_enabled=true`, `owner_admin_enabled=true`, revision 2, and scopes `diagnostic`, `exec`, `read_file`, `write_file`. This verifies authorization, **not** that the queued tasks are executing.
- No completed readback or cron output was returned. No new production snapshots were committed, and no existing job was resubmitted.
- The existing archived `S97xray` source manages `/opt/etc/xray/config.json` and has start/stop/restart branches. The archived `S99xray-watchdog` is a **different** service, not evidence that `S99xray` exists. The production inventory found `S97xray` and `S99xray-watchdog`, but did not list `S99xray`. Both production `xray-auto-update.sh` and `xray-safe-v23.sh` refer to `S99xray`. **Likely stale service reference, not yet a proven live fault:** actual cron invocation and whether `S99xray` exists must be checked read-only.
- The requested complete SHA256 comparison cannot be concluded without further router-side checksum results or independent hashing of all corresponding exact source bytes. Keep production hashes as reference; do not report hash equality without verification.
- **Safety:** no changes to production router, Xray, cron, firewall, routing or kill-switch.

## Queue state transition: running → unknown
Read-only polling of the same nine IDs showed a new outcome:
- `da2d6c64-d60d-4cc5-bd67-66b8b3a16908` (read_file `xray-watchdog-migrate-v25.sh`) now returns **status `unknown`**, with `created_at=2026-10-30T20:25:16.079Z` and unchanged `lease_until=1793392309114` (`2026-10-30T20:31:49.114Z`). No `output` or `exit_code` was returned. **Do not label it done or failed** without additional evidence; possible expired lease or missing job state requires investigation.
- The other eight existing IDs still return **queued**; no completed source content or cron inspection has been returned.
- Worker permission status remains `remote_enabled=true`, `owner_admin_enabled=true`, revision 2. This does not prove the router agent is polling or acknowledging jobs.
- **No duplicate submissions**, no new router jobs, no new source snapshots, and no production changes were made.
- Because there is no fresh cron output, `S97xray` versus `S99xray` remains an unverified mismatch. Because there are no new checksum results, full SHA256 equality remains unverified.

### Safe next diagnostic decision
Investigate the existing queue/lease handling and agent liveness via already-available read-only telemetry or Worker/GitHub source, without resubmitting these jobs. Preserve all nine IDs and their statuses. Do not unblock, cancel, or change the router or production until queue semantics are understood.

## Read-only incident investigation: unknown lease and blocked queue
Source reviewed in `ment2/keenetic-control`, branch `fix/worker-v5-auto-unblock`:
- `worker/src/coordinator.mjs` `expire(now)` (lines 28–38): expired `running` jobs become `unknown` with `outcome_unverified=1`; receipt/lease and unresolved `recovery_blocks` are retained. This explains the **observed** `running → unknown` transition as consistent with the reviewed implementation, but **deployed Worker source fingerprint is unverified**.
- `/claim` (lines 138–148) refuses further jobs while any `running` or unresolved `unknown` exists, explaining why queued jobs may not progress. This is intentional fail-closed behavior, not evidence that queued jobs were executed.
- `/results/:id` (lines 159–179) accepts matching-receipt late results for `unknown` and clears the recovery block; it does not rerun the original task. A receipt mismatch returns 409.
- The Worker also has a 1-hour queued-job expiry check (line 38). **Actual queued states must be checked before assuming the branch exactly matches production.**
- `agent/src/keenetic_agent.py` (lines 174–235) documents durable pending-result journal and refusal to replay uncertain operations; a `result_ready` record is only removed after acknowledged HTTP delivery. Archived agent implementation does **not** establish installed Agent identity.
- `docs/audits/agent-worker-auto-unblock-risk-2026-10-30.md` and `docs/audits/installed-agent-diagnostic-contract-2026-10-30.md` explicitly warn that Worker-only auto-unblock can conflict with Agent's durable claimed record. A root `read_file` job is not an attested safe auto-unblock candidate.

### Live observations
The original nine existing job IDs were polled again; `da2d6c64-d60d-4cc5-bd67-66b8b3a16908` returned `unknown` with lease `1793392309114` (`2026-10-30T20:31:49.114Z`); eight returned `queued`. No job was resubmitted. Permission state: remote enabled, owner admin enabled, revision 2. These facts do not prove Agent heartbeat or polling. No direct authenticated Cloudflare queue database or Agent journal/heartbeat read is exposed by the current read-only plugin methods; thus **agent liveness and exact failure of result delivery remain unknown**.

### Safe recovery plan (not executed)
1. Establish deployed Worker and installed Agent version/SHA via authorized read-only control-plane metadata or separately approved read-only filesystem telemetry; compare against reviewed GitHub branch. Do not assume candidate branch is production.
2. Inspect Durable Object read-only recovery state, audit trail and nine job records (state, lease, receipt presence, generation, blocked_job), **without exporting receipt values, tokens or payloads**. Determine whether the blocking job has a late result or was abandoned.
3. Inspect Agent heartbeat/last successful poll and **redacted journal metadata only** (claimed/result_ready/job_id/receipt presence, not receipt value), and identify whether result delivery is failing due to network/auth/lease mismatch. Avoid any command execution through the blocked queue.
4. If `result_ready`, use the existing Agent's normal **receipt-bound result delivery** only after validating installed contract; do not rerun command. If `claimed`/uncertain, keep blocked until operator-reviewed reconciliation proves safe.
5. Never auto-unblock, clear journal, reset receipt, requeue, or redeploy based solely on elapsed lease. Require explicit operator approval for any later mutation.
6. After recovery, poll existing jobs and inspect cron and service paths read-only, then compare exact production file SHA256 against GitHub snapshots. Preserve historical archive separately.

### Audit boundary
No new router jobs, no auto-unblock, no Cloudflare or router production mutation. No new production source copies or SHA256 equality claims because the existing jobs have not completed.

## Production snapshot branch update: recovered queue
Working branch: `snapshot/keenetic-production-2026-10-30` (main remains unchanged).

Owner's queue recovery is documented in `ment2/keenetic-control`, `docs/incidents/queue-recovery-2026-10-30.md` (branch `fix/worker-v5-auto-unblock`). Live follow-up on our **nine original job IDs** returned:
- `da2d6c64-d60d-4cc5-bd67-66b8b3a16908`: **failed**, exit -1, no source recovered. Do **not** re-execute this previously unknown operation without a separate safety decision.
- Seven other `read_file` jobs: **done**, exit 0. Copied their untruncated, nonsecret source to `xray/production/opt/bin/`: `xray-fc-recover.sh`, `xray-killswitch-enable.sh`, `xray-main-pid.py`, `xray-preflight-v24.sh`, `xray-control-selftest.py`, `xray-rollback-selftest.sh`, `xray-killswitch-test.sh`.
- Cron/checksum job `73553c5a-5253-455b-a760-5a8c6ea21e59`: **done**, exit 0, but initial cron search missed the actual root crontab.

An additional read-only inventory `b946db3b-956a-47b4-b14d-d1b42251ea0b` completed and confirmed:
- `/opt/etc/init.d/S97xray` **exists**.
- `/opt/etc/init.d/S99xray` **does not exist**.
- `/opt/etc/init.d/S99xray-watchdog` **exists** (distinct service).
- Actual root crontab path: `/opt/var/spool/cron/crontabs/root`, 1978 bytes; `/opt/etc/crontab` also exists. Earlier search omitted the actual root crontab, so absence of cron matches in that earlier output was inconclusive.
- Redacted cron inspection job `176488fc-bd06-42a7-9883-4ef14cc8295c` is queued; **do not requeue**.

### SHA256 byte-equivalence, VERIFIED
Computed SHA256 independently over GitHub UTF-8 file bytes and compared with live router `sha256sum` output. All **15/15** tested production snapshot files matched exactly:
`xray-fc-recover.sh`, `xray-killswitch-enable.sh`, `xray-main-pid.py`, `xray-preflight-v24.sh`, `xray-control-selftest.py`, `xray-rollback-selftest.sh`, `xray-killswitch-test.sh`, `xray-update-v23.py`, `xray-safe-hourly.sh`, `S96xray-killswitch`, `S98xray-wifi`, `xray-ks-home-watch.sh`, `xray-ks-home.sh`, `xray-wifi-rules.sh`, `xray-fc-cron-guard.sh`. SHA256 algorithm sanity-checked with standard `abc` test vector. This establishes equality for these **specific files at the sampled time**, not whole-router identity.

Six more untruncated, nonsecret readbacks were copied to the branch: `xray-update-v23.1.py`, `xray-control-v24.py`, `xray-control-v24-next.py`, `xray-identity-v24.py`, `xray-watchdog-migrate-v252.py`, `xray-watchdog-v25-service.sh`. Their SHA256 equivalence has **not yet been independently checked**.

### Outstanding queued readbacks
First group:
`c8390211-e4ab-4876-8193-5fa6b3a8ca9d`,
`284bbc5f-88dc-4d9c-a886-4738ea112cd2`,
`40a3b5cb-9c36-4082-82cc-97721cb6c68c`,
`6e138295-28fc-4735-8761-71062daa2729`.
Second group:
`58bf020d-4de1-4566-90e8-32c721b9bc20`,
`4bdabea8-a062-467c-a4f6-b3abe95b0d87`,
`e43f6831-68bb-47e4-bf31-d62925f2d401`,
`8a6f5447-bbfb-42f8-a134-e34fc8d1162d`,
`e3f31bf3-27fe-43a0-9ad4-9201c7eea972`,
`19ce61bc-b2ae-4f27-86d1-25c1bd970ad7`,
`cf0abe6f-d229-4844-a313-ec0bbdc26840`,
`e837bcd5-d386-410a-9b03-c282fd1b222b`,
`ba1d017b-ea65-4a9f-9352-a5f503e1c106`,
`9d71fd03-3475-4ef5-99d6-1ed90265193d`.

**Secrets excluded:** subscription URL, raw Xray config, tokens, credentials, Telegram sessions. GitHub branch is a nonsecret snapshot, not a raw full-disk clone. Router/Worker/Xray production remains unchanged by this audit.
