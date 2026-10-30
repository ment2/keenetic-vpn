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

## Verified CI checkpoint

- **41134367243 SUCCESS**: **84/84 offline tests** (72 previous + 12 dry-run safety tests).
- **41134447314 SUCCESS**: **84/84 tests** plus an actual synthetic CLI invocation of `first_migration_dry_run_v30.py` producing `NOT_AUTHORIZED` with empty `production_commands` because exclusive SOCKS5/TPROXY handoff is unproven. GitHub job step `Execute synthetic first-migration dry-run and assert NO DEPLOY` passed.
- **41134057510 SUCCESS**: Xray 26.2.6 linux/mipsle under QEMU, API BO/ADO/RMO TCP continuity on synthetic loopback.

**No real production inventory has been read or used in this dry-run.** Its SHA256/PID/ports are synthetic test inputs. The first-switch mechanism remains unimplemented and requires a future reviewed change request and separate approval.

## Executable isolated cutover/rollback fault model

Added `xray/lab/cutover_controller_v30.py` and `tests/test_xray_cutover_controller_v30.py`. This is an **executable Python simulator**, **not a router deployment script**. It never executes shell commands, binds production ports, accesses router files, or modifies iptables. Its `FakeProcess` objects, SOCKS/TPROXY readiness flags and `owner` pointer are deliberately synthetic.

Implemented:
- Exclusive nonblocking `flock` on a temporary local lab file; reject concurrent migration.
- CAS generation and `(PID,start_ticks)` identity checks before changing synthetic ingress ownership.
- Atomic JSON journal write with file and parent-directory `fsync`.
- Watchdog fence flag in journal, simulated readiness gates for SOCKS5, TPROXY and API, fail-closed check and no direct fallback.
- Fault injection before and after synthetic cutover; rollback to healthy old owner or blocked state if old owner unavailable.
- Recovery after simulated crash from prepared/switched journal, with process identity validation.
- Old TCP counter retained; no false claim that existing TCP sessions migrated.

**Important limitations before real cutover:** `handoff_proven=True` in the simulator is a *synthetic test flag*. It does not validate actual port rebinding, TPROXY, packet forwarding, real watchdog suppression or any kernel state. In-memory state and the JSON journal are not a complete crash-safe router transaction. A production implementation must re-read actual listeners and PIDs, implement safe port transfer/restart, watchdog fencing and out-of-band rollback, and prove all checks on matching KeeneticOS hardware. Never deploy the simulator to router.

CI **41134617393 SUCCESS** covered the 21 additional synthetic fault-injection tests, bringing the offline suite to **105 tests**. The source-contract workflow was further updated to execute the simulator demo explicitly and assert its output is marked `SWITCHED_SIMULATION_ONLY`; final CI result is recorded separately.

## Real dual-process MIPS32LE lab checkpoint

New `xray/lab/xray_v30_dual_process.py` launches **two real Xray 26.2.6 linux/mipsle binaries via QEMU** on disposable GitHub Actions runner, with **distinct loopback SOCKS listeners**, a synthetic local echo backend, and a candidate-only loopback API. It records real process PID and Linux `/proc/<pid>/stat` start ticks. The old TCP connection stays alive while new TCP uses the candidate's *different* SOCKS port; candidate is then terminated, and the old process continues serving TCP. GitHub CI **41134880794 SUCCESS** (both original API and new dual-process job steps passed). Static source-contract tests extended to **113** (105 previous + 8 lab contracts), CI **41134950130 SUCCESS**.

**Do not confuse client-selected ports with a real ingress handoff:** the test client deliberately connects to one of two independent SOCKS ports; there is no shared stable production listener, kernel TPROXY transfer, packet routing or actual watchdog process. A dead candidate listener refusing TCP is not equivalent to kernel fail-closed verification. The test does not measure first-cutover outage duration.

The lab has subsequently been extended with a local UDP echo backend and SOCKS5 UDP ASSOCIATE tests on both processes and after candidate failure; CI verification for that extension is tracked in the next run. UDP test is **SOCKS UDP only**, not TPROXY UDP.

### Outstanding gates
- Demonstrate a **real** stable ingress owner and controlled cutover with live port transfer or explicit bounded restart; prove no double listener and automatic rollback under a crash.
- Model watchdog race against real supervised processes (current `S97xray` killall is unsafe) and prove independent kernel fail-closed for TCP/UDP/DNS/IPv6.
- Prove MIPSLE QEMU API readiness and PID-specific recovery are compatible with actual KeeneticOS/Entware kernel and firewall.
- Obtain separate explicit approval for any router access or production change.

### UDP diagnostic: failed, not silently passed

CI **41135006860** and retry **41135112889** failed in the added SOCKS5 UDP ASSOCIATE handshake on the first real MIPSLE Xray process: the client timed out waiting for the initial SOCKS5 authentication response (5 seconds, then 15 seconds). Both Xray processes had started and reported real PID/start ticks. Root cause is **not established**; may be a configuration/routing issue or emulator behavior. Increasing timeout did not fix it. No claim of UDP continuity or UDP fail-closed is justified.

The previously successful dual-process TCP lab was restored to its known-working SOCKS `udp: false` configuration and UDP claims removed. The separate `UdpEcho`/UDP-associate probe remains in source for further isolated diagnostics but is **not invoked** by the TCP regression job. No production change was made. The UDP failure is a deployment blocker, not permission to bypass UDP through direct Internet.

## Latest verification checkpoint (dual process and races)

- **41135279245 SUCCESS:** two real MIPSLE Xray processes under QEMU with distinct loopback SOCKS ports; old TCP stream survives while new process handles TCP; candidate process killed; old process still accepts new TCP. Existing API continuity lab also passes.
- **41135363480 SUCCESS:** **117/117 offline tests**, including four deterministic synthetic watchdog-fence and competing-controller race tests in `tests/test_xray_cutover_races_v30.py`.
- UDP experiment **41135006860** and **41135112889** failed on SOCKS5 handshake, documented above. UDP path remains **unverified**. Latest passing dual-process test intentionally uses TCP-only SOCKS settings and makes no UDP continuity claim.
- No real watchdog was started, fenced or changed; no real TPROXY ingress handoff or kernel fail-closed test. Synthetic lock and journal tests are not substitutes for live process supervisor verification.

**Decision:** Do not authorize production migration based on these tests. Next engineering work is a fully isolated *stable ingress owner* with actual client-to-process redirection and rollback, separate UDP diagnosis, and watchdog race integration using a disposable watchdog implementation (not the production `killall` script). Production untouched, no merge/deploy.

## 2026-10-31 UDP handshake root cause resolved in disposable MIPSLE lab

The previously failed SOCKS5 UDP test used **double-escaped byte literals** in its Python wire-format client. It sent literal backslash/x text instead of binary SOCKS5 greeting bytes. Increasing timeout was ineffective because the client request was malformed. The isolated lab client was corrected, and real MIPSLE Xray 26.2.6 under QEMU now passes **SOCKS5 UDP ASSOCIATE** on both independent loopback SOCKS listeners and again on the old process after the candidate is terminated. It also preserves the prior TCP continuity and rollback assertions.

**GitHub CI 41136096595 SUCCESS**. Log markers: `PASS SOCKS5 UDP ASSOCIATE on both processes`, `PASS UDP old process after candidate failure`, `PASS old TCP stays alive while candidate handles new TCP`. The synthetic UDP echo uses an outbound `freedom` redirect **only to 127.0.0.1** as a test fixture; it is not a real VPN route and does not establish production fail-closed. The lab's default config remains UDP-disabled for static contract compatibility; its integration invocation explicitly enables UDP. These results supersede the earlier failed UDP diagnostic, but **do not** establish TPROXY UDP, kernel kill-switch, a stable production ingress port, or real watchdog coordination.

**Remaining blockers:** actual ingress handoff and rollback on one stable port, real TPROXY TCP/UDP, supervised watchdog race, fail-closed kernel policy. No production changes authorized or made.
