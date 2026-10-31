# Keenetic Xray v30: cooperative supervisor staging and independent crash recovery

Date: 2026-10-31. Repo `ment2/keenetic-vpn`. **Only** branch `feature/xray-v30-stable-tcp-ingress-lab-20261031`. No GitHub main/snapshot change, merge or production deploy.

## Owner scope and result

Owner approved replacing global `killall` with exact PID/start-ticks management, introducing a common lock covering S97/watchdog/S98 and proving independent recovery in an isolated laboratory. Owner also instructed to continue until a real blocker and to provide a continue action on pauses.

**Completed in feature branch:** staged cooperative supervision primitives and candidate service/entrypoints; independent **real Linux process** crash/rollback laboratory; multiple CI green runs. **NOT completed:** deployment to Keenetic, live MIPS pidfd compatibility proof, atomic migration from the legacy unfenced supervisor, live Xray TPROXY cutover/reboot recovery. No production `--trial`, `--rollback`, `--guardian` submitted.

## Staging code, immutable Git blob IDs

| Path | Git blob SHA | Responsibility |
| --- | --- | --- |
| `xray/staging/v30_supervisor_core.py` | `d4c11b4159604170af210ca9e05e9c7f1268b112` | root-only flock, strict process PID/start_ticks/exe/argv, pidfd signals without `os.kill` fallback, fsynced journal and compatibility PID files, gated fork/exec |
| `xray/staging/v30_supervisor_service.py` | `ba3cb7805a755b770b983b9ec0de40ac966cae45` | single broker for S97 scoped start/stop/restart, watchdog health check, lock-held S98 Wi-Fi rule repair with kill-switch prerequisite, watcher identity bootstrap/start/stop |
| `xray/lab/v30_fenced_process_recovery_lab.py` | `114abf963979abd3a5f5a462bc5b073c84c47dc9` | disposable loopback TCP/UDP legacy+candidate process fault-injection and detached guardian |
| `tests/test_xray_v30_supervisor_core.py` | `edee399c37faad06331f86a0ec42f7e268bbc1e0` | real-process flock/recovery/gated-spawn, PID reuse, private journal tests |
| `tests/test_xray_v30_supervisor_service.py` | `9876e42ba463e6fc0a0157ed8449555c23c53264` | mock service tests, watchdog/supervisor scoped signals, S98 fail-closed rule repair, watcher bootstrap and PID files |
| `tests/test_xray_v30_supervisor_templates.py` | `4c89a564234c13f0373cc418138e38a4f3ce871a` | shell syntax and broker-only entrypoint checks |

Five **staging-only** shell entrypoint templates:
`xray/staging/v30_supervisor_templates/S97xray`,
`S98xray-wifi`, `S99xray-watchdog`,
`xray-watchdog.sh`, `xray-wifi-rules.sh`.
They contain no executable global `killall`. These are **not** drop-in approved production artifacts, and a migration must verify that no cron or other legacy process invokes the unfenced originals.

## Actual isolated runner experiments and evidence

- GitHub Actions [41204979115](https://github.com/ment2/keenetic-vpn/actions/runs/41204979115): **SUCCESS**, 284/284 offline tests and actual two-loopback-port isolated process experiment. A controller acquired the shared flock, shut down only the test old service, spawned candidate after durable identity journal, and was **SIGKILLed** while holding the mutex. The detached guardian waited for the kernel to release the lock, terminated the identifiable test candidate, restarted original test service and successfully probed **TCP + UDP**.
- GitHub Actions [41205827337](https://github.com/ment2/keenetic-vpn/actions/runs/41205827337): **SUCCESS** with two fault injection points: (1) controller death after `candidate_running` and (2) controller death immediately after the durable `candidate_prepared` PID/start-ticks journal, **before** committing the candidate transaction phase. Both tests independently restored old loopback TCP/UDP using detached guardian. This limits candidate PID journal-loss window in the synthetic controller.
- GitHub Actions [41206064404](https://github.com/ment2/keenetic-vpn/actions/runs/41206064404): **SUCCESS, 314/314 tests** (includes pure + mock + actual test processes). Previous interim failed runs were test fixture/mock formatting and were resolved; a green final CI was checked against its exact head commit.
- Existing GitHub MIPS32LE QEMU workflow separately checks official Xray v26.2.6 in other lab scenarios, **but the new detached guardian demo uses disposable Python TCP/UDP endpoints**. It does NOT yet prove that a live Xray MIPS32LE candidate will recover under identical fault injection, nor TPROXY kernel UDP, DNS/IPv6 or power-loss recovery.

## Production status/compatibility read-only tools

- Existing Keenetic installation (from prior successful stage): old active Xray, corrected inactive canary `/opt/bin/v30_first_cutover_canary.py` SHA256 `8e57ef5054f53174a35d906d34eab073dd6d787607cb02f29d83364ae3abc203`, old S97/S98/S99/watchdog remain unchanged.
- Single read-only `router_status` job `4861e527-fa5c-43da-a84d-a7f5672448b8`: **done, exit_code=0**; Keenetic ONLINE, Python 3.13.9, Linux, load (0.49,0.72,0.74), free disk 3.49 GB.
- Single bounded read of `/proc/sys/kernel/osrelease` job `6e65e44d-3f82-4ba9-89a5-f5ac64e47d3b`: **done, exit_code=1**, `operation_failed`. Did **not** retry or substitute arbitrary exec after prior OpenAI safety system block. Actual kernel version, `pidfd_open` and `pidfd_send_signal` support **UNKNOWN**.
- New broker **deliberately refuses target signaling** when kernel/Python pidfd is unavailable, rather than fall back to `killall` or PID-racy `os.kill`.

## Hard release blockers (do not ignore)

1. **Real Keenetic kernel supports pidfd? Unknown.** Must use an explicitly authorized, supported, read-only capability diagnostic, never bypass the prior blocked command. Old Linux kernels may not support pidfd even if Python 3.13 exposes the functions.
2. **Legacy source migration race.** Legacy `S97xray` still uses global `killall xray`; old watchdog and S98 may have spawned descendants not protected by the new lock. Merely installing a new broker does not make the currently running legacy scripts cooperative. Require a separately approved identity-scoped two-phase cutover with proof all direct repair/restart entrypoints are migrated and no unfenced descendant remains.
3. **Canary integration absent.** The currently installed `v30_first_cutover_canary.py` uses a different transaction lock, and has pinned hashes for the old S97/S98/S99/watchdog sources. Replacing those init scripts would make its current `--plan` fail. A new complete, pinned canary and independent recoverability review are required before any new trial.
4. **Partial migration recovery.** Staged supervisor start spans separate prepared/pidfile/active journals, which are individually atomic, but a whole multi-file deployment, reboot and guardian crash replay have NOT been proven end to end. The staged broker still needs dedicated recovery of each interrupted step and physical router test.
5. **Network proof.** Linux loopback TCP+UDP process demo is not MIPS Xray transparent TPROXY. QEMU MIPS + kernel namespace may lack `IP_TRANSPARENT`; DNS/IPv6 no-leak and kill-switch fail-closed must be separately measured.
6. **Exact file install approval.** Keenetic Mobile queue operations require each absolute target path/full contents/exact approved action before allowing `confirmed:true`; this generalized goal approval is not unconditional permission for an unreviewed replacement of S97/S98 or a trial.

## Recommended next engineering steps

Continue with isolated MIPS32LE Xray guardian fault injections and staged atomic boot/partial-upgrade recovery; audit cron and all legacy script entrypoints read-only via supported diagnostics; produce a full rollback package and atomic release manifest for every changed file; validate kernel pidfd support on real router **using an approved, non-bypassing read-only method**. Then obtain exact-file approval to stage (not automatically activate) replacement packages. Only perform one live trial after a fresh independent release gate. Never conflate 314 passing tests with production safety.

**Current disposition: offline supervisor design and standalone process recovery proof available; production change NOT PERFORMED due to real unresolved compatibility and safe-migration gates.**
