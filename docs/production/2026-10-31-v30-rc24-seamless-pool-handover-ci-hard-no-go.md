# RC24: seamless VPN subscription pool handover, verified real MIPS32LE Xray API, production HARD NO-GO

**Date:** 2026-10-31  
**Repo/branch:** `ment2/keenetic-vpn` / `feature/xray-v30-stable-tcp-ingress-lab-20261031` ONLY.  
**Objective:** Refresh verified endpoint pool without restarting Xray or disrupting established TCP connections. This report deliberately ignores unrelated SLIRP/MIPS UDP research from earlier RCs.

## Verified changes to pool refresh safety

1. `xray/lab/pool_generation_v30.py`: in-memory generation CAS is serialized with `RLock`, freezes mutable proposal input, recomputes `reconcile` at commit, refuses tampered/stale plans, and persists **only qualified** endpoint fingerprints (excluding all `failed`). Reorder and standby additions preserve current active endpoint. Empty/all-failed refresh does not overwrite last-known-good. It does **not** itself block ingress to a dead last-known-good endpoint; that requires the live ingress owner and kill-switch.
2. `tests/test_xray_v30_seamless_pool_refresh_cas.py`: 11 unit tests verify active stickiness, standby, disqualification, stale/forged plan, double concurrent CAS (exactly one winner), immutable snapshots, invalid API/continuity gate and empty pool. No credentials or production connection.
3. `xray/lab/xray_v30_pool_handover_api.py`: real pinned MIPS32LE Xray 26.2.6 user-mode QEMU runner performs API `ado` + `bo` with synthetic isolated loopback echo backends. It verifies A kept when still in qualified pool (no `bo`), new-only TCP switches to C after removal/disqualification, already-established TCP stays on A, then **actually stops C backend**. New connections cannot silently route direct or fall back to A, pre-existing A TCP survives, explicit `bo` to A restores new connections. PID/start-ticks of the same process and stable SOCKS listener port are asserted throughout.
4. `.github/workflows/xray-v30-rc24-seamless-pool.yml`: disposable runner, SHA256-pinned official MIPS32LE Xray 26.2.6 zip `1590b2bcefe64fb0604f29c8c75219bfbe8f63daa3bc8e3956edfa6da97c5869` and binary `3d2588c5ef770a6a7e1bfdd5db511130fb3acd79eb91bfcb108753b3e1dda1f6`. Tests and real API handover are explicitly required markers; logs are uploaded on CI and no deployment steps exist.

## GitHub Actions evidence

| Run | Outcome | Specific proof |
|---|---|---|
| [41235753728](https://github.com/ment2/keenetic-vpn/actions/runs/41235753728) | **SUCCESS, 618/618** | All offline regression tests after pool CAS changes |
| [41235798140](https://github.com/ment2/keenetic-vpn/actions/runs/41235798140) | **SUCCESS** | 9+10+11 targeted tests and real MIPS Xray A kept / C new flows / A rollback |
| [41235844421](https://github.com/ment2/keenetic-vpn/actions/runs/41235844421) | **SUCCESS** | Real selected C backend failure, no silent direct fallback, old A TCP still alive, explicit API rollback |
| [41235943877](https://github.com/ment2/keenetic-vpn/actions/runs/41235943877) | **SUCCESS** | 30 targeted tests, real pinned MIPS Xray same PID/start-ticks/SOCKS port through A keep / new C / candidate death / rollback. Job `124639636002`, all steps SUCCESS. |

Latest log markers from [41235943877](https://github.com/ment2/keenetic-vpn/actions/runs/41235943877):
```
POOL_API: PASS new qualified pool retains active A; no BO switch
POOL_API: PASS changed pool sends new TCP to C; old A TCP survives
POOL_API: PASS dead selected C blocks new TCP while old A survives
POOL_API: PASS explicit BO rollback restores new TCP to A
POOL_API: PASS SAME_MIPS_XRAY_PID_STARTTICKS_AND_SOCKS_PORT_THROUGH_REFRESH_FAILURE_ROLLBACK
POOL_API: NOT TESTED automatic leastPing, VLESS, UDP, TPROXY, router firewall
```

## Exact blockers to safe deployment

1. **Existing production Xray process has no enabled API.** Real `bo`/`ado` cannot be applied to that already-running process. Enabling API by rewriting active config or using `S97xray` (which contains `killall xray`) is **not seamless**. Initial ingress ownership migration to an API-enabled process or separate stable ingress has not been approved or proven on the physical device.
2. **No end-to-end real VPN test:** the proven API mechanism uses synthetic freedom redirects to 127.0.0.1 echo backends, not real VLESS/REALITY server health, OpenAI/Telegram eligibility, authentic 5-tuple routing, TPROXY UDP or IPv6/DNS fail-closed. Selection based solely on `leastPing` could change active endpoint independently of pool refresh; explicit verified current-endpoint policy is required.
3. **No durable production coordinator:** current CAS is process-memory only. No production-safe fsynced transaction log/lock, live active endpoint identity, watchdog fencing and safe/atomic crash rollback. Actual legacy root process escape from cgroup v1 and S97/S98/S99/watchdog/cron races remain hardware blockers. This is not solved by simulator success.
4. **Hardware/recovery:** Keenetic KN-1810 vendor MIPS `4.9-ndm-5`, USB-independent rescue and verified restoration of originals have not passed physical acceptance. No consent to live trial or production changes.

## Decision

**`RC24_DISPOSABLE_MIPS_API_TCP_SEAMLESS_POOL_REFRESH_SUCCESS`**  
**`HARD_NO_GO_PRODUCTION`** until separately authorized and verified first migration of stable ingress/API, watchdog isolation and rollback.

**Prohibitions maintained:** no Keenetic jobs, no main/snapshot/production/Cloudflare/firewall/routes/cron mutations, no merge/deploy/live trial. Next work should remain *exclusively on seamless pool handover*: identify minimally disruptive first API/ingress migration and its exact rollback, then obtain separate explicit user approval before any physical change.
