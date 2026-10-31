# Keenetic Xray v30 RC4: exact-generation guardian CAS, sealed orphan inventory, review rescue archive and Linux 4.9 release runbook

**Date:** 2026-10-31. Repo: `ment2/keenetic-vpn`. **Only branch:** `feature/xray-v30-stable-tcp-ingress-lab-20261031`.

**Decision:** RC4 SOURCE/LAB **PASS**; physical Keenetic production **NO-GO**. No router jobs, prod changes, merge, deploy or live trial.

## Independently checked CI

- [**41214978812**](https://github.com/ment2/keenetic-vpn/actions/runs/41214978812): **SUCCESS, 444/444 offline tests**, latest feature-branch head `8b4496e79bb06ba61e2b861da6724378b3772f0e`. Verified exact hash manifests, sealed inventory failures, two competing cohorts of real guardian processes, deterministic five-file rescue archive, and no-production release gates.
- [**41214849008**](https://github.com/ment2/keenetic-vpn/actions/runs/41214849008): **SUCCESS, 439/439 tests** on workflow introduction. GitHub Actions artifact **`v30-kernel49-offline-rescue-review-rc4`**, artifact ID **13047593479**, 14-day retention, published after verifying all five frozen script bytes and read-only metadata. This artifact is **not bootable** and does not live outside the Keenetic Entware USB.
- Earlier real official **Xray 26.2.6 linux/mipsle** in disposable QEMU user-mode: [**41213319142**](https://github.com/ment2/keenetic-vpn/actions/runs/41213319142), **SUCCESS**. Three serialized concurrent S97 restarts, S98/S99/watchdog/cron cooperative requests, parent and guardian crash, independently restored SOCKS5 TCP and UDP. RC4 changes are offline protocol hardening; there is **no new QEMU MIPS CI run for the RC4 generation-CAS code itself**. Its two guardian generations were tested as real independent Python processes on the runner.
- Archived read-only diagnostic `ea140581-a4db-42f5-ac4d-46c8c6c462ba` previously recorded Keenetic **Linux `4.9-ndm-5`** and loaded `xt_TPROXY`. No new read-only probe or router job was submitted. The prior pidfd supervisor cannot work on Linux 4.9.

## 1. Stronger guardian fencing: exact owner generation and claim tokens

Existing `xray/staging/v30_kernel49_cooperative_ledger.py` was extended, with exact Git blob SHA `1da7d48499f22fd1fc56c4b3a528a366fc3d3c8c`, to add:
- `begin_scoped_recovery(expected_generation, guardian_ticks)`: under the same short-lived shared flock, binds recovery to the exact crashed owner generation, records one claimant and makes an in-flight request durably `UNCERTAIN`.
- `takeover_scoped_recovery(old_claim, guardian_ticks, verified_old_guardian_dead)`: CAS over the prior claim including its random token. A later stale claimant cannot take over after this changes. No TTL expiry or signal to an unknown PID.
- `finish_scoped_recovery(claim, proof)`: commits only the matching claim/generation, requires seven independently verified LAB-only absence proofs, cancels pending stale operations as `CANCELLED_UNCERTAIN` and does not silently replay them. This never authorizes production.
- The old synthetic `reconcile_for_lab` now refuses to operate while an exclusive new recovery claim exists.

A disposable lab `xray/lab/v30_guardian_generation_race.py` (Git blob `5faeae528f80c8070ce1ca694ef8e50f9773f308`) started **eight real independent guardian processes** racing for one owner generation. Exactly one claimed. The runner killed that winner. Another **eight** raced to take over using the original claim, exactly one succeeded; the old attempt could no longer commit. The final durable ledger contained exactly one `UNCERTAIN` restart receipt and one cancelled queued cron health request, with the new parent generation advancing exactly once.

**Boundary:** `verified_old_guardian_dead` and other recovery proof flags in this lab are supplied by disposable test harness. They are **not a verified live kernel 4.9 process-identity attestation** and cannot be trusted for router deployment.

## 2. Stronger descendant inventory: explicit limits of /proc snapshots

`xray/lab/v30_sealed_descendant_inventory.py`, Git blob `73cc5da16c121a9a54ad30fd972aa7360bb7c629`, provides offline **two-consecutive-snapshot** invariant checks for:
- exact PID/start-ticks, executable/argv and parent PID with identity drift detected;
- previously sealed membership of one isolated process scope, complete enumeration, and all legacy restart/rules/cron writers inside that scope;
- TCP/UDP socket inode ownership, unknown sockets, unreadable `/proc` metadata and changed membership;
- any surviving group member, including renamed and reparented grandchild processes, causing **NO_RESTART**;
- Linux 4.9 group/cgroup capability not presumed present.

The model tests simulate orphaned grandchild that renamed itself, PID reuse, unattributed TCP/UDP socket, unreadable processes, scope escape, swapped PID identity and different snapshots.

**Critical:** even two identical `/proc` scans cannot establish that no process forked/escaped between scans without kernel-enforced containment established *before* the original Xray launched. A full independent scoped PID + socket inventory on the physical router is still unverified. The tool's synthetic `SYNTHETIC_DRAIN_CONTRACT_ONLY` explicitly retains `production_recovery_authorized=false`.

## 3. Reproducible non-executable rescue review archive

New `xray/lab/v30_review_rescue_bundle.py`, Git blob `cc6f8907193bf007546ff599429dc663ecca9efd`, constructs a byte-for-byte deterministic USTAR archive `v30-kernel49-rescue-review.tar` from **only** the five archived original scripts: S97, S98, S99, watchdog and Wi-Fi rules. Every original byte is checked against RC1 frozen SHA256 source pins.

The archive includes a canonical `rescue-metadata.json` describing exact SHA256 and original 0755 mode, but each tar member is deliberately stored as **0600, non-executable**. Its parser rejects symlinks, hardlinks, duplicates, unsafe paths, re-packed or corrupted data and attempts to claim release authority. It contains **no executable boot guardian**, Xray binary, Python runtime, init activation script, Cloudflare secrets or production restore commands.

GitHub Actions published it under run [41214849008](https://github.com/ment2/keenetic-vpn/actions/runs/41214849008), artifact `v30-kernel49-offline-rescue-review-rc4` (ID `13047593479`); the standard 14-day artifact retention is **not** a durable router storage guarantee. This verifies a reviewable recovery source package only, NOT actual USB-independent physical recovery.

## 4. Versioned RC4 release manifest

`xray/staging/v30-kernel49-rc4-rescue-review.json` pairs RC4 with the unchanged RC3 `xray/staging/v30-kernel49-cooperative-boot-rescue-v1.json`. Its SHA-pinned components are the ledger, double-inventory contract, multi-process guardian CAS lab and rescue review bundle generator. It records real CI IDs and retains all hardware safety gates **false**. `tests/test_xray_v30_rc4_release_manifest.py` rejects hash drift and any fabricated hardware approvals.

No work was done in main, snapshot or any deployed router source. The only code/workflow changes are in this feature branch.

## 5. Compatibility matrix: archived Linux 4.9 vs lab

| Requirement | Isolated runner evidence | Physical Keenetic evidence | Disposition |
| --- | --- | --- | --- |
| `pidfd_open` and `pidfd_send_signal` | Not used in Linux 4.9 alternative | Historical `4.9-ndm-5`, syscalls unavailable | **MUST NOT USE** |
| Direct-parent `waitid(WNOWAIT)`, `waitpid`, `PR_SET_PDEATHSIG` | Real MIPSLE user-mode process trial succeeded, host kernel Ubuntu | No live router proof; Xray may create detached descendants | **UNVERIFIED** |
| Atomic private flock/ledger and exact generation CAS | Linux runner concurrent process trials succeeded | Current S97/S98/cron not migrated; lock path possibly USB-backed | **UNVERIFIED** |
| Isolated cgroup v1 process membership and socket inode completeness | Adversarial synthetic snapshot tests only | cgroup v1 mounts, permissions and containment not read from router | **UNVERIFIED** |
| Kernel TPROXY IPv4 TCP+UDP | Native x86 netns experiment passed | Only historical `xt_TPROXY` evidence; no new real cutover | **UNVERIFIED** |
| DNS, IPv6 no leaks, kill-switch continuity | Partial older tests only | No full current physical host proof | **UNVERIFIED** |
| Boot guardian and rescue independent of Entware USB | Deterministic archival recovery package, not an executable rescue | No proven separate durable mount, cold boot or USB removal proof | **UNVERIFIED** |

## 6. Exact safe release runbook (REVIEW-ONLY, no commands to execute)

**Stage A: offline release review.** Compare immutable 9-file RC1 manifest, 5-file original rollback pins, RC2 parent-owned lab and RC3/RC4 source pins. Review all proposed target path/contents/mode. Confirm independent offline rescue and fallback config. Never install an unreviewed template.

**Stage B: approved non-disruptive inventory.** With separately authorized read-only capability, collect real `uname`, cgroup v1 mounts/controllers, actual mount IDs/devices, Xray foreground/descendant process trees, PID/start-ticks, process FD/socket inode ownership, cron and boot restart paths, and current kill-switch/TPROXY rules. Only owner-authorized read-only calls and no duplicates/bypasses. If any device, permission, process, or writer is unknown: **STOP, NO CUTOVER**.

**Stage C: independent physical rescue requirement.** Prove backup/boot executable outside Entware USB is accessible after a cold reboot **with USB unavailable**, on a physically separate persistent device. Verify root ownership, exact hashes and immutable installed rollback. A GitHub Actions artifact or two directories on one USB **DO NOT SATISFY** this condition.

**Stage D: two-phase live migration design, not authorization.** Identify and cooperatively fence every old S97, S98, S99, watchdog, cron and their complete descendant trees *before* introducing any replacement. If cgroup support unavailable, develop a different demonstrably sealed scope or fail closed; two /proc snapshots alone are insufficient. The new owner never signals a non-child or sends global `killall`.

**Stage E: bounded production pilot only after explicit owner approval.** Separate owner approval must specify exact byte hashes, target paths, permissions and rollback action. Independent guardian must be proven to recover after the installer, owner, child, and first guardian die, including USB loss. Current task **does not authorize or run this stage**.

**Rollback invariants:** never replay `UNCERTAIN`; no partial writes with missing/corrupt backup; do not signal stale process IDs; verify complete old source hashes before changing any file; never open kill-switch or silently route traffic directly after recovery failure; retain independent audit/journal receipts.

## 7. Current blocking conditions

1. No proven physically sealed process group/descendant containment on Keenetic Linux 4.9.
2. No live independent guardian/cgroup/USB evidence or current production cron and parent/child inventory.
3. No physical bootable recovery path without Entware USB.
4. New RC4 generation CAS path was validated in host-process lab, **not on the MIPS QEMU or Keenetic kernel**. Prior RC3 MIPS integration remains green.
5. No explicit approval of exact production file replacements or trial, and existing production canary still pins old sources.

**Bottom line:** Offline CI **444/444 SUCCESS**, historical real MIPS runner **SUCCESS**, review archive produced and verified; **PRODUCTION/DEPLOY/MAIN/SNAPSHOT/CLOUDFLARE/ROUTER ALL UNCHANGED**. No new Keenetic jobs, cron modifications, route/firewall/kill-switch changes, merges or live trials.
