# Xray v30 RC1: two-phase legacy migration, independent rescue proof boundaries, MIPS boot replay and Linux 4.9 pidfd hard blocker

**Date:** 2026-10-31. **Repository:** `ment2/keenetic-vpn`. **Branch only:** `feature/xray-v30-stable-tcp-ingress-lab-20261031`. **No changes to main, snapshot, production router or Cloudflare. No router jobs submitted in this stage.**

## Verified CI on this feature branch

- [**41210443484**](https://github.com/ment2/keenetic-vpn/actions/runs/41210443484) **SUCCESS, 375/375 offline tests** on head `8b1ded835bd858bd8378be196c6f28453267b915`. Includes nine-file RC1 integrity pins, separate versioned five-file rescue specification, two-phase sequencing and descendant/cron checks, USB-loss and corrupt backup refusal, independent fresh-process restoration, mount/boot evidence checks, and precise archived Linux 4.9 pidfd rejection.
- [**41209958229**](https://github.com/ment2/keenetic-vpn/actions/runs/41209958229) **SUCCESS**, actual **Xray 26.2.6 linux/mipsle** via `qemu-mipsel`: killed the controller and *both original guardian processes*, launched a fresh recovery interpreter reading persisted on-disk journal, then independently recovered the original MIPSLE Xray SOCKS5 TCP and UDP ASSOCIATE. **Process restart only; no actual kernel reboot**.
- Previous native x86 [**41209311676**](https://github.com/ment2/keenetic-vpn/actions/runs/41209311676) **SUCCESS**, 3 disposable kernel TPROXY IPv4 TCP+UDP probes with fail-closed after Xray death. This does **not** establish MIPS QEMU kernel TPROXY.
- Historical experimental MIPS QEMU **kernel TPROXY** runs [41192637559](https://github.com/ment2/keenetic-vpn/actions/runs/41192637559), [41192734192](https://github.com/ment2/keenetic-vpn/actions/runs/41192734192), and [41192977345](https://github.com/ment2/keenetic-vpn/actions/runs/41192977345) FAILED with `failed to set IP_TRANSPARENT > protocol not available`. PREROUTING/TPROXY packet counts increased but intercepted TCP connection timed out. This failure is a **QEMU user-mode socket translation/kernel interoperability gap**, not proof that the physical MIPS Keenetic kernel is incapable of transparent routing.

## Hard evidence: the archived Keenetic is Linux 4.9 and pidfd is incompatible

A **previously completed read-only Keenetic diagnostic** `ea140581-a4db-42f5-ac4d-46c8c6c462ba` recorded **kernel `4.9-ndm-5`** and loaded `xt_TPROXY` with existing TPROXY TCP+UDP rules, listener, and table 100. This historical evidence is already documented in `docs/production/2026-10-31-tproxy-udp-watchdog-first-migration-gates.md`. The job was **not** requeued/reexecuted.

Linux `pidfd_send_signal` was introduced in kernel 5.1; `pidfd_open` in kernel 5.3. A 4.9 kernel **cannot execute** the existing staging supervisor's `os.pidfd_open` + `signal.pidfd_send_signal` path. Python 3.13.9 being installed does NOT add those kernel syscalls. New `xray/lab/v30_archived_kernel_pidfd_gate.py`, its tests and CI now explicitly issue **`OFFLINE_KERNEL_INCOMPATIBLE`**, not a guessed current live status. The historical kernel may have changed since that job; only a separately permitted read-only observation can establish current physical host capabilities.

**DO NOT** replace `pidfd` with a bare `kill(pid)` after a point-in-time `/proc` check and call it safe. PID reuse can occur between the check and signal. Alternatives needing fresh engineering include a **long-lived parent owning the Xray child until wait/reap**, strict socket ownership/child lifetime management, a separate independent and reboot-surviving rescue path, and fail-closed behavior when that parent disappears. A child-owned PID retention scheme is not yet implemented or proven as an integrated production supervisor; a non-parent guardian must never blindly signal by stale PID.

## Review-only two-phase migration plan

Machine-readable contract: `xray/lab/v30_two_phase_migration_contract.py` (new) and tests `tests/test_xray_v30_two_phase_migration_contract.py`. Input release pins remain in `xray/staging/v30-release-manifest-v1.json`.

1. **PREPARE**: verify exact nine-file staged release, all five frozen originals, independent rescue hashes/fsync, actual rescue path/boot accessibility, and an independently verified fail-closed kill-switch. No file writes or service actions before these checks.
2. **FREEZE_EXTERNAL_SPAWNERS**: inventory and *cooperatively* fence every way legacy services can start: `S97xray`, `S98xray-wifi`, `S99xray-watchdog`, `xray-watchdog.sh`, `xray-wifi-rules.sh`, plus `xray-fc-cron-guard.sh` and `xray-safe-hourly.sh`. Never assume the cron staging-only script cannot indirectly restart code without inspecting current live cron.
3. **DRAIN_DESCENDANTS**: take complete process/tree inventory including reparented workers and `killall xray` descendants; verify executable, argument vector, PID/start-ticks and service generation. Parent `SIGSTOP` alone is insufficient. **Do not send signals to ambiguous identities**.
4. **STAGE_ALL_FILES**: stage, but do not activate, new reviewed S97/S98/S99/watchdog/wifi-rules, broker, compatible canary and rollback package. Enforce one shared lock; fsync all writes and intent. This stage is NOT authorized on real router yet.
5. **VALIDATE**: prove all launchers cooperate, no child remains in flight, exact binaries/cfg/iptables/route and TCP+UDP/policy tests, recovery on the actual kernel, hardware USB and cold-boot rescue, and new release-owner permission.
6. **ACTIVATE**: would require a separate exact-path/byte/mode owner approval and a verified kernel 4.9-safe supervisor. If any invariant fails, abort without changing production.
7. **MONITOR**: enforce 30/60-second supervisor cycles, kill-switch persistence, TCP+UDP, DNS/IPv6 no leaks, independent guardian.
8. **COMMIT**: only after restored-safe/health evidence and documented exact deployed hashes. A phase skip/replay is rejected by the test contract.

**All eight stages are review-only proposals.** The module never invokes a router command and refuses to claim production permission even with all synthetic evidence true.

## Versioned five-file rollback contract

`xray/staging/v30-rescue-contract-v1.json` pairs with RC1 manifest and pins five original archive source bytes, SHA256, and file mode **0755** (Git mode `100755`) for S97, S98, S99, `xray-watchdog.sh` and `xray-wifi-rules.sh`. `tests/test_xray_v30_rescue_contract.py` verifies source hash equality with exact archived files. It is a **reviewable rollback specification**, **not** an installed rescue image or automatic production recovery permission.

`xray/lab/v30_nonusb_rescue_lab.py`: on an ephemeral Linux runner, made private test copies of actual original and new scripts, fsynced a separate rescue directory, killed an updater at 2/5 replacements, removed the normal USB-simulated backup, and proved a fresh process could restore 5/5 archived bytes using **only the separate rescue directory**. Corrupting even one independent rescue file caused **zero additional writes**. **The two directories are on the runner and do not prove separate hardware devices or survival of a physical Keenetic USB removal/reboot.**

`xray/lab/v30_outofusb_mount_gate.py` requires distinct mount ID, distinct kernel major:minor device and source, a persistent filesystem (not tmpfs/overlay), and independent *cold-boot, no-USB, guardian execution and SHA256 evidence*. Tests reject same-device or fake directory separation. Without actual host evidence its result is `INSUFFICIENT_EVIDENCE`, `production_rescue_authorized=false`.

## Why no actual deployment or test on router

**Production release remains a hard NO-GO** for two substantive reasons:

1. Archived kernel 4.9 lacks pidfd: current new supervisor is fundamentally incompatible, not merely awaiting a quick `--plan` confirmation. Must implement **and separately prove** a safe parent-owned/cooperative backend or other robust exact-identity mechanism compatible with real 4.9.
2. No independent persistent boot rescue proven outside the Entware USB and no safe live cutover/migration of legacy cron, S97 and S98 descendants. Hardware reboot/USB loss proof and full MIPS native TPROXY/VLESS/DNS/IPv6/fail-closed test remain unavailable.

**Change record:** only feature-branch GitHub code/tests/workflows/docs. No Keenetic router jobs queued, no PID signals, no production config or binaries, watchdog/S98/crons, firewall/routes/kill-switch, Cloudflare, main/snapshot, merge/deploy or live `--trial` changed. The previously installed first canary SHA256 `8e57ef5054f53174a35d906d34eab073dd6d787607cb02f29d83364ae3abc203` stays untouched.

**Next safe engineering track:** build a Linux 4.9-safe supervised Xray child ownership proof and independent guardian contract on disposable runner, including sudden parent/child death, PID reuse, and reboot replay; separately examine supported out-of-USB rescue locations using read-only evidence with explicit approval if needed. Only after those hard gates could exact new release bytes and a separately authorized router installation be proposed.
