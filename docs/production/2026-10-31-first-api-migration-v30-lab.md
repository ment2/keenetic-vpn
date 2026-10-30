# Xray v30 — first API migration: isolated safety design, no production changes

Status: **NOT READY FOR LIVE MIGRATION**. Existing Xray is 26.2.6 linux/mipsle and has **no API**. This document is a laboratory design and safety gate, not executable deployment instructions.

## Verified source-level blockers

- `S97xray` starts Xray with `/opt/sbin/xray run -config /opt/etc/xray/config.json` and `stop_xray` uses **`killall xray`**. Thus a normal restart kills all Xray instances including a temporary test instance, and established connections may drop.
- `xray-watchdog.sh` checks whether `127.0.0.1:10808` is listening, then calls `S97xray restart` if not. A port ownership transition can trigger an unsafe global kill even when a healthy candidate is running.
- `S98xray-wifi` checks TPROXY mangle chains and local route table 100, and invokes `xray-wifi-rules.sh` when checks fail. The real traffic entrypoint is TPROXY `0.0.0.0:12345` and local SOCKS `127.0.0.1:10808`; a new Xray process cannot simultaneously bind these exact addresses/ports without a separately verified handoff mechanism.
- Existing firewall/kill-switch watches are separate from Xray and must remain fail-closed. Neither `SO_REUSEPORT` nor Linux socket descriptor transfer is verified for installed mipsle Xray.
- A new API-enabled process can be launched on **different loopback test ports**, but that alone does not take over existing TCP/TProxy sessions or production listeners.

## Safe architecture decision

**Option A (recommended only after explicit migration approval):** one-time controlled cutover to an API-enabled Xray process with an explicit maintenance/interruption budget. Subsequent subscription refreshes use `ado`, `bo`, `rmo` without restarting that process, retaining current active VPN endpoint when qualified. The initial cutover cannot honestly be advertised as zero-downtime with the present single-process listener topology.

**Option B (more work, potentially continuity-friendly):** introduce a durable ingress/dispatcher that owns both SOCKS5 and TPROXY routing, and sends only *new* flows to new Xray while existing flows drain on old Xray. Must prove conntrack, SO_MARK/TPROXY, UDP association, DNS, source-IP transparency, and firewall invariants on matching KeeneticOS/MIPSLE before selection. A basic TCP proxy on SOCKS5 alone is insufficient for TPROXY. This requires production changes and is **not approved**.

## First migration state machine (pure offline simulation)

`legacy -> prepared -> draining -> api_enabled` with rollback from `prepared` or `draining` to `legacy` only if the legacy process is verified healthy. A *proven* ingress handoff is an explicit prerequisite; it is not implemented by the simulator.

- **Prepare:** candidate config validated, API loopback accessible, no direct/freedom fallback, firewall fail-closed, watchdog fenced (in a real implementation without disabling protection), generation and process identities captured, candidate uses separate ports. Legacy owns ingress and remains alive.
- **Cutover:** requires independent evidence of exclusive listener ownership and TPROXY/SOCKS correctness; new flows switch only after ingress handoff verified; legacy remains alive until existing sessions drain.
- **Finish:** only after measured drain and candidate health checks; preserve a durable rollback journal and clear watchdog fence safely.
- **Rollback:** requires healthy legacy owner and a verified reverse ingress handoff. In the simulator the reverse handoff is an abstract assertion, **not** a real network operation. If legacy is dead, fail closed rather than route to dead process or bypass VPN.
- **Watchdog:** legacy watchdog `killall` is prohibited during any transition. A future controller must implement PID/start-ticks-specific supervision and transaction-aware fencing. The simulator returns `alert_only` while fenced; it does not modify the real watchdog.
- **CAS:** generation mismatch and concurrent cutover are rejected. Real implementation additionally requires OS-level lock and durable state with fsync and crash recovery.

## Fail-closed and acceptance gates

1. No outbound `freedom`/direct in the **real VPN process**; synthetic loopback `freedom` redirects in disposable CI labs are not production fallback. Explicit blackhole for unmatched routes, DNS/IPv6 policy, and independent kernel kill-switch verification.
2. Invalid/empty qualified pool, stale generation, failed API, watchdog race, candidate death, failed TCP/UDP probe => no activation, old working process untouched. If old process also fails, traffic must block, not go direct.
3. Verify SOCKS5, TCP, UDP, DNS, TPROXY, kernel marks and real client flows separately. A successful SOCKS5 synthetic echo is not proof of TPROXY continuity.
4. Verify rollback of both control plane and data plane after partial cutover, including interrupted controller/reboot, and that no two Xray processes own the same production listeners.
5. Verify MIPSLE parity: Xray 26.2.6 linux/amd64 CI passes `bo`/`ado`/`rmo` and preserves unrelated TCP flows, but **Go build and architecture differ**. Do not copy amd64 binary to router. Official mipsle release availability and ABI/runtime compatibility must be confirmed; binary version string alone is not enough.
6. Explicitly confirm acceptable **first-migration outage budget** and rollback conditions with user before any production change.

## CI evidence

- `41132772990` SUCCESS: Xray 26.2.6 amd64 isolated loopback `random` and `leastPing` strategies, dynamic API `bo`/`ado`/`rmo`, old TCP continuity.
- `41132870489` SUCCESS: 52 offline tests for snapshot, updater, staging, watchdog, identity, pool policy and generation CAS.
- New `xray/lab/first_migration_model_v30.py` and `tests/test_xray_first_migration_v30.py`: 20 fault-injection tests for ingress ownership, watchdog fencing, drain, rollback, generation, direct fallback and fail-closed. **Simulator does not perform actual network handoff.**

No merge, deploy, router jobs, production Xray/cron/firewall/routes/watchdog/kill-switch modifications.
