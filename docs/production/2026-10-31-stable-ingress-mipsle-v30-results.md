# Xray v30: stable SOCKS5 TCP ingress and rollback laboratory

Date: 2026-10-31. Scope: **only** `ment2/keenetic-vpn`, branch `feature/xray-v30-stable-tcp-ingress-lab-20261031`. Not deployed.

## Verified evidence

- GitHub CI [41190544759](https://github.com/ment2/keenetic-vpn/actions/runs/41190544759): **SUCCESS**, 142/142 offline tests. Frozen 63-file production snapshot matches GitHub manifest, **not a live router check**.
- GitHub CI [41190533716](https://github.com/ment2/keenetic-vpn/actions/runs/41190533716): **SUCCESS**, actual Xray **26.2.6 linux/mipsle** (MIPS32LE) processes executed via QEMU on disposable GitHub runner.
- New `xray/lab/stable_socks_ingress_v30.py`: loopback-only stable TCP byte relay; CAS generation and PID/start-ticks identity; atomic selector update for **new** TCP sessions; old TCP sessions remain on old backend. No implicit retry to provider/direct when selected candidate dies; rollback to verified old backend, or block if old identity unavailable.
- New `xray/lab/xray_v30_stable_ingress_demo.py`: two **real** Xray processes with distinct SOCKS5 TCP backend ports and one stable lab client-facing TCP port. GitHub job printed:
  - `PASS old TCP survives real Xray selector cutover`
  - `PASS new TCP fails closed after candidate crash`
  - `PASS old restored on SAME TCP ingress port`
  - `PASS PID/start-ticks and generation gates`
- New `tests/test_xray_stable_ingress_v30.py`: 11 unit contracts (port stability, drain, rollback, stale CAS, PID reuse, readiness, fail-closed and loopback). Branch CI ran 142 total tests, up from 131.
- Both GitHub workflows expanded to run on the isolated feature branch. No merge to main or archival snapshot branch.

## Meaning and non-claims

This proves a **stable loopback TCP SOCKS front-end in a disposable environment**, not that the existing Keenetic production listener can be switched without interrupting real traffic. The ingress is a Python test relay and **is not a production-ready supervisor or TPROXY proxy**. The real Xray backends are configured SOCKS UDP-disabled, with a synthetic loopback freedom redirect to a local echo fixture only. No real VPN secret, subscription, OpenAI server, or external route used. No packet-loss/outage bound is established.

**Still unverified:** 0.0.0.0:12345 transparent TPROXY for both TCP/UDP, stable 127.0.0.1:10808 ownership during *initial* migration, DNS/IPv6 leaks and kernel kill-switch, watchdog `S97xray` global `killall xray` race, actual VLESS server qualifications and OpenAI/Telegram traffic, persistent journal/lock on router, reboot recovery. Current production Xray has **no API**, so the first API-enabled migration cannot be assumed seamless.

## Next safety gate

1. Read-only live inventory: Xray binary/config hashes (no secret config contents), actual PID/start-ticks, ingress ownership, init/watchdog/cron, iptables/ip rule/table 100, firewall/kill-switch invariants. Never enqueue duplicate jobs on a timeout.
2. Extend disposable lab to test TCP/UDP TPROXY and a race with a synthetic PID-scoped watchdog. Verify no path to direct Internet and instrument loss/continuity for **new vs existing** flows.
3. Produce an exact versioned first-migration/rollback plan with out-of-band recovery, watchdog fencing, local private backups and explicit interruption tolerance. The first port-owner change likely cannot be zero-downtime.
4. Keep current production updater staging-only and **preserve existing SOCKS5 10808** during all future changes. Do not generate Telegram memory events as network smoke tests.

## Production state

No router commands submitted in this feature work, no production config edits, no Xray restart, no route/cron/firewall/kill-switch change, no merge/deploy. This laboratory result **does not authorize** production cutover.

## Follow-up: subscription pool continuity on real MIPSLE Xray

New `xray/lab/xray_v30_pool_handover_api.py` exercises actual Xray 26.2.6 linux/mipsle `ado` and `bo` with the existing pure `reconcile` / `Coordinator` logic. **GitHub CI [41190821835](https://github.com/ment2/keenetic-vpn/actions/runs/41190821835) SUCCESS**; real disposable process logs:

- `POOL_API: PASS new qualified pool retains active A; no BO switch` (new standby C is added without sending BO for the still-qualified endpoint A).
- `POOL_API: PASS changed pool sends new TCP to C; old A TCP survives` (active A removed/disqualified from new pool).
- `POOL_API: PASS explicit BO rollback restores new TCP to A`.

The endpoints are synthetic local echo servers, not real VPN. An injected health gate requests explicit BO rollback; automatic leastPing fallback, OpenAI reachability, real upstream failure and production stability are NOT proven.

## Read-only router parity checkpoint

- Read-only diagnostic `711886cd-0a0e-4317-a10c-1080353dd767`: **done, exit 0**, Keenetic ONLINE, load ~0.9, available disk 3.53 GB.
- First attempted read-only shell job `d4b68bc2-ebdd-4d88-8592-ee3154afe0d1`: **done, exit 2**, shell quoting syntax error; no changes, do not repeat.
- Corrected read-only job `3d9343ec-7266-4268-8b68-0c9ec73d43c7`: **done, exit 0**. Xray version `26.2.6 linux/mipsle`, PID **13546**, start_ticks **100216734**.
- Current config SHA256 `66d074f32fffbf4a251576c8297714e9647174546e9e73e5bf27cf2768efe6d7`; matches previously recorded live hash.
- Xray binary SHA256 `680db07db2b5d53080bfecb8752bc830c6a890367aa3bc57d42d4660506591f2`.
- S97xray init SHA256 `87ea1dc13a9be95d57c0595d7a7f13b03fe97bd56ab1f144a3c94d57cc588d5d`.
- S99xray-watchdog SHA256 `e8423e15ed2cf4d3662e5725d27d6e58bd08bbdd807b47fcabe30391ac4c738b`.
- xray-watchdog.sh SHA256 `dddcc1d324e30b91df041378645ada869a18b4d35f2842383e5d319fc859e08`.
- TCP listeners present at `127.0.0.1:10808` and `:::12345`; fwmark `0x40000000/0x40000000` priority 20000 routes to table 100; table 100 `local default dev lo`. This is **not** a full iptables or leak audit.

No Xray restart, no files written to router, no firewall, route, cron or watchdog changes.

## Final deployment gate

The new-pool API mechanism now passes a synthetic real-MIPSLE test, but **the current production Xray has no API** and its current init script uses global `killall xray`. A zero-downtime first migration of both SOCKS5 10808 and TPROXY 12345 remains unproven. Before production activation require separate explicit approval of exact maintenance cutover/rollback commands and a tolerated disruption window, plus TPROXY/UDP/kernel fail-closed and watchdog fencing verification.
