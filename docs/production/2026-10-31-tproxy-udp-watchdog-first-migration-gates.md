# Xray v30 first-migration evidence, UDP/dokodemo lab, watchdog races and cutover gate

Date: 2026-10-31. Repository: `ment2/keenetic-vpn`. Branch: `feature/xray-v30-stable-tcp-ingress-lab-20261031`. **LAB ONLY; NO PRODUCTION DEPLOY OR LIVE CUTOVER.**

## Verified results

- CI [41192265396](https://github.com/ment2/keenetic-vpn/actions/runs/41192265396): **SUCCESS**; 179/179 offline tests, static source contracts, synthetic no-deploy check, 63/63 frozen GitHub snapshot files match manifest (not fresh router comparison).
- CI [41192207473](https://github.com/ment2/keenetic-vpn/actions/runs/41192207473): **SUCCESS**; official Xray 26.2.6 linux/mipsle under QEMU. Existing API BO/ADO/RMO, stable TCP SOCKS ingress and pool-preservation tests passed, plus a new *real* dual-process `dokodemo-door` TCP/UDP loopback test. Log messages: `PASS real MIPSLE TCP and UDP on both isolated dokodemo listeners`, `PASS old TCP/UDP after candidate crash; old TCP flow survives`.
- New `xray/lab/xray_v30_dokodemo_lab.py`: two separate loopback dokodemo TCP/UDP listeners and synthetic local TCP/UDP echo destinations; candidate death followed by old-process service continuity. `followRedirect=false`; NO kernel transparent packet interception. `freedom` is used ONLY for loopback echo test fixtures, NOT a direct Internet VPN fallback.
- New `xray/lab/watchdog_policy_v30.py`: read-only decision-only watchdog model; rejects PID reuse via `/proc/<pid>/stat` start-ticks comparisons, stale generations, broken journal and unsafe kill-switch; during fence or in-flight cutover it returns `observe_only` and **never sends signals, restarts Xray or changes routes**.
- New `xray/lab/migration_readiness_v30.py`: 19 independent evidence gates. All missing gates -> `BLOCKED`. Even a synthetic all-pass can yield only `READY_FOR_SEPARATE_OWNER_APPROVAL`, with `deploy_authorized=false` and `production_commands=[]`.
- New tests: `tests/test_xray_watchdog_policy_v30.py`, `tests/test_xray_dokodemo_v30.py`, `tests/test_xray_migration_readiness_v30.py`. CI total increased from 142 to **179**.
- Updated `.github/workflows/xray-v30-mips32le-lab.yml` on feature branch to run real dokodemo TCP/UDP; unchanged `main`, `snapshot`, actual Entware/Xray, firewall and cron.

## Live baseline (existing result only; no new router job)

Router job `3d9343ec-7266-4268-8b68-0c9ec73d43c7`: `done`, exit=0. Xray 26.2.6 linux/mipsle, PID 13546, start-ticks 100216734; live config SHA256 `66d074f32fffbf4a251576c8297714e9647174546e9e73e5bf27cf2768efe6d7`; binary SHA256 `680db07db2b5d53080bfecb8752bc830c6a890367aa3bc57d42d4660506591f2`. SOCKS5 TCP 127.0.0.1:10808 and TCP :::12345 listening. Routing rule fwmark 0x40000000/0x40000000 -> table 100, `local default dev lo`. This result **did not verify UDP ownership, TPROXY rules or actual packet flow, kernel fail-closed, DNS, IPv6 or active endpoint**; do not re-use historical PID as a kill target.

Frozen production source review:
- `S97xray` calls `killall xray` on stop/restart. Unsafe in a two-process handover.
- `xray-watchdog.sh` checks only the SOCKS listener and may run that restart every 30 seconds on failure; `S99xray-watchdog` supervises it.
- `S98xray-wifi` periodically checks/repairs TPROXY mangle rules (60 seconds). `xray-wifi-rules.sh` **flushes XRAY_WIFI** before rebuilding it; a concurrent repair must be treated as an independent cutover race.
- `xray-ks-home.sh` maintains a forward-chain DROP for Home traffic. Presence of a source file is not evidence that active rules are fail-closed right now.
- `xray-safe-hourly.sh` stages `config.pending.json` only. Do not turn its staging into an implicit deploy.

## First migration: gated maintenance plan (proposed, NOT authorized)

**Suggested window:** 02:00–02:30 Moscow time on a date explicitly chosen by the owner. Reserve an additional 15 minutes for verification. No guaranteed 30-minute recovery. Any actual interruption depends on tested rollback and may exceed the window if it fails. User must explicitly accept interruption of existing TCP/UDP; it cannot be promised zero.

1. **T-24h to T-1h: preflight and dry-run.** Re-read production hashes and live PID/start-ticks, listener *owners* (TCP+UDP), IPv4/IPv6 firewall, `iptables -t mangle`, `XRAY_WIFI`, `XRAY_KS_HOME`, `ip rule` and route table 100; inspect watchdog and Wi-Fi repair process identities, updater/cron; validate backup readback and restore to nonproduction paths. All secrets and backups stay on the router; export only redacted facts/hashes. Verify an out-of-band/local recovery channel independent of VPN.
2. **T-1h: candidate rehearsal, no ingress change.** Build API-enabled candidate on unused local ports with `run -test`, `127.0.0.1`-only API and no Internet freedom/direct outbound. Qualify each VLESS server, OpenAI reachability and Telegram transport separately; test TCP, UDP, DNS and IPv6, verify actual fail-closed. Do not touch 10808, 12345, firewall, cron or kernel routes.
3. **T-30m: supervisor and rollback acceptance.** Before any production work, prove a PID/start-ticks-scoped supervisor and *transaction-aware* fencing for `S97xray`, `xray-watchdog.sh`, `S98xray-wifi`, and the hourly updater. No global `killall`, no disabling the kernel kill-switch, no unbounded suspension of route repair. Capture durable generation journal with atomic fsync and an independently runnable local rollback script. Exercise crash before/after first bind, partial TCP/UDP ownership and simulated reboot. **If ANY test fails, CANCEL.**
4. **T=02:00: owner-approved first cutover.** Requires a second approval for an exact reviewed command bundle and confirmed maintenance window. Old production Xray has no API and owns both ports. A controlled PID-specific stop/rebind may interrupt existing sessions; do NOT claim seamless migration on this first step. After exclusive listener ownership for SOCKS5 10808 and TPROXY 12345 is proved, activate API-enabled generation, preserving kernel mark/table-100/kill-switch invariants. Never call legacy `S97xray restart`.
5. **T+0–30s: fail-fast readiness.** Require SOCKS5 end-to-end, TPROXY TCP/UDP from a dedicated client, OpenAI, Telegram transport, DNS/IPv6 leak absence, verified process identity/start ticks and API loopback health. Failure/unknown result at 30s => trigger pre-tested PID-scoped rollback using the private last-known-good bundle; if old owner cannot be restored, **fail closed**, no direct fallback. This is a policy trigger, not a guaranteed 30s rollback completion.
6. **T+30s to T+30m: observe and drain.** Confirm new flows via qualified VPN, old flows drain on old process where feasible, preserve stable SOCKS5 DNS path for dependent clients. Watch for 30/60-second supervisor cycles, API and health failures, packet loss, route/iptables drift; abort on loss of critical invariants. Only after acceptance resume staged subscription policy; no automatic activation of untested pools.
7. **Post-change:** record real PID/start-ticks, config/script SHA256, permissions, exact deployed versions, rollback evidence, live end-to-end tests and incident log to both GitHub feature branch and `/Keenetic/Xray/` Library. Merge/deploy only with distinct approval.

**Rollback matrix:** bad candidate/API, identity or generation drift, missing exclusive UDP/TCP ownership, watchdog race, failed route/kernel rule, any leak/direct fallback, failed Telegram/SOCKS dependency => abort or roll back. Unknown rollback target => traffic stays blocked and use out-of-band recovery.

## Current blockers / next evidence needed

1. **Real kernel TPROXY** `followRedirect`, `SO_MARK`, `fwmark`, `XRAY_WIFI`, TCP/UDP and original-destination preservation, preferably in a disposable Linux network namespace, then on compatible KeeneticOS with explicit approval.
2. **Stable UDP ingress** and UDP flow draining (separate from SOCKS5 UDP ASSOCIATE and loopback dokodemo); DNS/IPv6 leak/kill-switch evidence.
3. **Real watchdog and Wi-Fi-rule repair fencing** under current 30s/60s loops; no global `killall` and no rule-flush gap during cutover.
4. **Exact executable first-migration and local rollback scripts** only AFTER kernel/supervisor ownership and cold-restore tests pass. Do not generate a live one-click migration from this lab.
5. **Fresh router preflight and interruption approval**. Existing permission to access router is not authorization for an unknown disruptive command. No new router jobs were submitted in this work.

**Decision today: BLOCKED for first production cutover. All work is confined to this feature branch and the ChatGPT Keenetic/Xray project.**
