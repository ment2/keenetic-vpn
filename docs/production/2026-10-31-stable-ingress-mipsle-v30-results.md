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
