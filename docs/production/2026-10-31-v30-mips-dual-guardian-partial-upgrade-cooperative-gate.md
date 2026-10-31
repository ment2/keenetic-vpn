# Keenetic Xray v30 — real MIPSLE dual-guardian failover and frozen five-file partial-upgrade recovery

**Date** 2026-10-31. **Repository** `ment2/keenetic-vpn`. **Branch** `feature/xray-v30-stable-tcp-ingress-lab-20261031`. No changes to main, snapshot branch, existing router/Cloudflare or production config, no merge/deploy. This is an isolated feature-branch lab, NOT live production approval.

## Summary: verified, not assumed

- **[GitHub Actions 41207498806](https://github.com/ment2/keenetic-vpn/actions/runs/41207498806) — SUCCESS**: real Xray **26.2.6 MIPS32LE** under `qemu-mipsel`, with loopback SOCKS5 TCP and SOCKS5 UDP ASSOCIATE; three independent controller/guardian crash injections, all returned verified legacy Xray TCP/UDP.
- **[GitHub Actions 41207211999](https://github.com/ment2/keenetic-vpn/actions/runs/41207211999) — SUCCESS**: initial real-MIPSLE recovery at `candidate_running` and at `candidate_prepared`, while killing the first guardian under the single flock, second guardian took over.
- **[GitHub Actions 41207385790](https://github.com/ment2/keenetic-vpn/actions/runs/41207385790) — SUCCESS, 320/320 unit tests**: explicit shared-lock cooperative canary release check, and two isolated partial-upgrade experiments. In the stronger one, **the five original archived source files and their five actual staged replacements** were used. A test updater was killed after 2/5 source files were replaced, and a separate interpreter restored all five original bytes, checking SHA256 and modes and fsynced intent journal.
- The production snapshot itself was never modified; release-compatibility checks use copies, with no secrets or external VPN providers.

## Exact implementation references

1. `xray/lab/v30_mips_guardian_failover.py`: Git blob SHA `fee51ee613f3447809aa3c248e79e2306066bc68`. Two real MIPSLE Xray processes use a **single** loopback SOCKS5 TCP+UDP port sequentially. The controller owns a private `flock`; durable `candidate-prepared` records the candidate PID/start-ticks before exec. Two detached Python guardian interpreters wait for a verified controller failure. First guardian is deliberately killed while owning `flock`, optionally **after terminating the candidate with a pidfd-scoped signal** but before old Xray is restored. The second guardian acquires the lock and restores old real MIPSLE TCP/UDP ingress, verifying test echo and matching original logical service.
2. `xray/lab/v30_partial_upgrade_recovery.py`: Git blob SHA `21b75dfdebe4c4c9475de2d62eac23164a62c7d5`. Disposable updater copies **real frozen archived** S97/S98/S99/watchdog/wifi rules files and real staged candidate bytes into separate private directories, pre-fsyncs the full manifest and per-operation intent, deliberately dies after two replacements; a separate recovery interpreter restores original hashes/modes on all five paths. Rejects symlinks, unknown content and corrupt backups. Neither copies nor changes actual `/opt/` paths.
3. `xray/staging/v30_cooperative_canary.py`: Git blob SHA `c2864dfb5c0eee319d438a5e63a927b32cca79cc`. Pure offline release contract establishing common `/opt/var/run/xray-v30-supervisor.lock` for `S97`, `S98`, watchdog, cutover and guardian; checks all five staged entrypoint bytes, broker core, and requires positive proof no legacy restart/rule repair remains. Its only CLI mode is `--offline-plan`; **no production trial is implemented** and its response explicitly marks `production_trial_allowed=false`.
4. The staged broker and core from previous milestone remain unchanged: `xray/staging/v30_supervisor_core.py` Git blob `d4c11b4159604170af210ca9e05e9c7f1268b112`, `xray/staging/v30_supervisor_service.py` `ba3cb7805a755b770b983b9ec0de40ac966cae45`. Five staging shell entrypoints exist in `xray/staging/v30_supervisor_templates/`. The **installed production canary** is different, currently pinned to original S97/S98/S99 hashes and a different mutex; it was **not** changed in this stage.

## Real crash matrix (successful on disposable runner)

| Case | Failure injection | Proof from job logs |
| --- | --- | --- |
| A | Controller killed after real MIPSLE candidate binds TCP+UDP; primary guardian killed holding lock before repair | Secondary restored original MIPSLE Xray; TCP + UDP ASSOCIATE passed |
| B | Controller killed just after durable `candidate_prepared`, before committed `candidate_running`; primary guardian killed | Secondary read prepared PID journal and independently restored original Xray, TCP+UDP passed |
| C | Controller killed at committed candidate; primary guardian stops candidate with PID-scoped signal and dies before legacy restart | Secondary resumed from partial rollback state, restored MIPSLE TCP+UDP |
| D | Five-file update killed after 2/5 replacements (synthetic content fixture) | Fresh process independently restored all five original hashes and modes |
| E | Five-file update killed after 2/5 replacements (**actual frozen source bytes**) | Fresh process independently restored all five original archived SHA256 and modes |

No real router PID, init, iptables, routes, cron or kill-switch was touched. No `--trial`/`--guardian`/`--rollback` was sent to Keenetic.

## Verified CI output highlights

```text
MIPS_GUARD: PASS two real Xray 26.2.6 MIPS32LE processes via QEMU
MIPS_GUARD: PASS SOCKS5 TCP and UDP ASSOCIATE old/candidate/restore
MIPS_GUARD: PASS primary guardian fault at after_candidate_stop
MIPS_GUARD: PASS independent secondary restored real MIPS Xray TCP+UDP
PARTIAL_UPGRADE: PASS real frozen legacy and staged replacement bytes 5/5
PASS: cooperative canary and S97/S98/S99 staging share lock; live trial remains forbidden
Ran 320 tests ... OK
```

## Critical remaining **real** blockers

1. **Live Keenetic Linux pidfd not verified**. Prior approved `router_status` job `4861e527-fa5c-43da-a84d-a7f5672448b8` returned ONLINE, Python 3.13.9, ~3.49 GB free. The single separate read of `/proc/sys/kernel/osrelease` job `6e65e44d-3f82-4ba9-89a5-f5ac64e47d3b` failed `operation_failed`. No new router job attempted in this turn. No tool-safety workaround or duplicate submissions.
2. **Actual legacy descendants remain active under unfenced source paths**. Existing `S97xray` uses global `killall xray`; `S98xray-wifi` can spawn independent iptables mutator. A release must prove all cron/watcher/init entrypoints cooperate before any live cutover. The new broker templates are staged only.
3. **Live canary incompatible** with these new replacement artifacts: old pinned hashes and different transaction lock. A new complete integrated, SHA-pinned production candidate and documented, atomic staged-to-live deployment procedure still need separate, exact-file approval.
4. **Not kernel TPROXY**: this MIPSLE experiment tests localhost SOCKS5 TCP/UDP, not real TPROXY route/mark/PREROUTING, IPv6/DNS leak, fail-closed VPN routing, real VLESS upstream, or physical Keenetic/USB outage. Linux user-mode QEMU does not substitute for exact Keenetic kernel behavior.
5. **Reboot/power loss not proven**: primary guardian crashes and parent controller kill are tested as *process faults*, not full machine restart. No proof of physical boot persistence or child process cleanup after USB loss.

## Next safe work

Continue feature-only integration: versioned full release manifest pinning actual candidate hashes; isolated live Xray 26.2.6 kernel TPROXY experiments where runner kernel supports them; prove startup and rollback of coordinated S97/S98/watchdog with a full parent/child process tree and mid-update reboot simulation. Only use owner-approved read-only diagnostics for Keenetic capability; if unavailable, document blocker rather than bypass. For any production installation require exact new bytes/path/mode and explicit separate approval. No merge/deploy or silent cutover.

**Decision: offline MIPS + dual-guardian + five-file rollback VERIFIED; production v30 migration NOT YET SAFE/AUTHORIZED.**
