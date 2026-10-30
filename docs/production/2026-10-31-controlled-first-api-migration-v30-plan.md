# Keenetic Xray v30 — controlled first API migration: execution plan (NOT AUTHORIZED)

**Status:** Design and offline dry-run only. No production command in this document is approved or executed. Branch: `snapshot/keenetic-production-2026-10-30`.

## Decision and interruption estimate

Chosen strategy: **one-time controlled maintenance cutover** from existing Xray 26.2.6 linux/mipsle without API to API-enabled Xray, followed by future dynamic pool updates through `ado` / `bo` / `rmo`. The first migration cannot be promised as seamless: current SOCKS5 `127.0.0.1:10808` and TPROXY `0.0.0.0:12345` are owned by the legacy process. The current init script uses `killall xray`; watchdog may invoke that restart on port loss.

**Outage budget is not measured.** Planning allowance: reserve **5–10 minutes of maintenance window** with an immediate rollback trigger after **30 seconds of failed readiness** (policy proposal, not a proven recovery time). Actual connection disruption may be seconds to minutes, and could exceed the window if rollback fails. Existing TCP and UDP sessions can be lost on the first restart. A 5–10 minute maintenance window is not a 5–10 minute guaranteed outage or recovery bound.

## Phase 0 — evidence and approvals (READ-ONLY)

- Record exact current `config.json` SHA256 and encrypted local backup, Xray binary SHA256/version, PID plus `/proc/<pid>/stat` start ticks, and system uptime.
- Record `netstat -lntup` listeners, Xray API absent, SOCKS5 and TPROXY ports, IPv4/IPv6 routes, table 100, fwmark, `iptables -t mangle -S`, `iptables -S`, `ip6tables -S`, watchdog process/cron/init service, updater schedule and staging-only status.
- Record current pool endpoint identities, actual active endpoint (if observable), subscription generation and last-known-good without exposing credentials or real addresses in GitHub.
- Capture expected external tests for OpenAI API (unauthenticated 401 means reachable), Telegram MTProto separately, DNS and leak checks; collect baseline timings.
- Confirm router free memory, disk, CPU and MIPS32LE binary parity. Official Xray 26.2.6 linux/mipsle under QEMU passed BO/ADO/RMO continuity in CI **41134057510**, but router kernel behavior remains untested.
- Backups must remain on router/private storage, never committed to GitHub. Record only non-secret hashes and redacted summaries.

## Phase 1 — fully offline preparation (DONE FOR MODEL; NOT FOR REAL ROUTER)

- Validate API-enabled config with `xray run -test` **against an isolated candidate file**, without replacing production config.
- Candidate API must bind **127.0.0.1 only**, not WAN; no external API exposure. Candidate test instance, if authorized in a future stage, must use nonproduction listener ports and a **PID-specific** supervisor.
- Ensure no real VPN route to `freedom`/direct fallback; unmatched traffic must blackhole, kill-switch must remain effective. This is a **migration requirement**, not a claim about the current active config. Distinguish legitimate LAN bypass rules from Internet fallback.
- Prepare durable rollback bundle: exact old config, old init/watchdog versions, old PID/start ticks, current firewall/route snapshots, SHA256 and permissions, and a local recovery procedure that does not require VPN access.
- Dry-run program `xray/lab/first_migration_dry_run_v30.py` takes a **synthetic** JSON inventory and emits a non-executable report. It refuses cutover while ingress handoff is unproven. It never emits executable production commands.

## Phase 2 — maintenance-window cutover (FUTURE, REQUIRES SEPARATE APPROVAL)

**No ready-to-run migration script is provided because the real SOCKS5/TPROXY ownership transition and watchdog fencing have not been validated on KeeneticOS.** Before approval, produce exact versioned, reviewed, tested scripts and rollback commands with captured PID/start-ticks and expected output. Do not call existing `S97xray restart` or `killall xray`.

Proposed order:
1. Obtain explicit user approval for exact commands, maintenance window and rollback threshold.
2. Acquire exclusive OS lock; recheck generation CAS, live process identity, SHA256, backups, WAN/LAN reachability, and kill-switch.
3. Fence legacy watchdog restart **transactionally** while keeping independent fail-closed enforcement and an out-of-band recovery path. Do not stop kill-switch, route watchdog or TPROXY monitoring.
4. Stage validated API-enabled process and verify localhost API/SOCKS on separate test ports.
5. Switch ingress ownership only using a previously tested mechanism. For a simple restart-based first migration, expect old TCP/UDP sessions to break; avoid pretending old sessions can drain after the legacy process is stopped.
6. Confirm exclusive listeners on 10808 and 12345, API responsiveness, SOCKS5/TPROXY traffic via VPN, OpenAI, UDP/DNS/IPv6 behavior and fail-closed.
7. On any gate failure or readiness exceeding proposed 30-second threshold, execute independently tested rollback to the known-good config/process. If rollback cannot restore a healthy VPN, **keep fail-closed**, never bypass VPN.
8. After verified health, install PID-scoped transaction-aware watchdog supervision, resume staging-only subscription refresh (until dynamic controller separately approved), and record generation/journal. Verify across subsequent watchdog cycles.

## Rollback matrix

| Failure | Required response |
|---|---|
| Invalid candidate, API probe failure, bad SHA, missing backup | Abort before touching live process |
| Generation/PID mismatch, concurrent updater | Abort; do not kill/restart process |
| Legacy watchdog not safely fenced | Abort; prevent global `killall` race |
| API-enabled process fails to bind 10808 or 12345 | Trigger tested rollback; retain kill-switch |
| SOCKS5 succeeds but TPROXY fails | Roll back; SOCKS-only success is insufficient |
| OpenAI fails for all new pool members | Retain last-known-good if viable; otherwise fail closed |
| UDP/DNS/IPv6 leaks or direct Internet fallback | Abort/rollback, preserve block |
| Controller crashes mid-cutover | Recover from durable journal, verify actual PID/start ticks and listener owner before action |
| Rollback fails | Keep traffic blocked and require local/out-of-band recovery |

## Remaining prerequisites for executable change request

1. A **real** pre-cutover inventory with hashes and non-secret live facts; all test values in CI are synthetic.
2. An exact, locally tested and independently recoverable first-switch mechanism for **both** SOCKS and TPROXY; no confirmed zero-interruption mechanism.
3. Durable journal, OS lock, watchdog fencing, PID-scoped rollback, source-controlled scripts and fault injection under a matching environment.
4. Define a user-approved maintenance window, readiness threshold and explicit interruption tolerance.
5. Only then request separate approval for the exact live actions.

## CI references

- **41133986994** SUCCESS: 72 offline source/model tests.
- **41134057510** SUCCESS: real official Xray 26.2.6 MIPS32LE under QEMU, API BO/ADO/RMO, TCP continuity for synthetic loopback connections.
- `tests/test_xray_first_migration_dry_run_v30.py`: 12 additional safety tests for fail-closed and approval gates; report status must be verified in CI.

**Production unchanged. No merge. No deploy. No restart.**
