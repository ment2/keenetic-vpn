# Keenetic Xray v30 RC5: real MIPS32LE 8+8 guardian CAS, Linux 4.9 containment, USB-free boot-rescue acceptance

**Date:** 2026-10-31. **Repository:** `ment2/keenetic-vpn`. **Only branch:** `feature/xray-v30-stable-tcp-ingress-lab-20261031`.

**Disposition: RC5 LAB PASS; physical production HARD NO-GO.** All tests are disposable. No router jobs, no Cloudflare, no production Xray, no S97/S98/S99/cron/firewall/routes/kill-switch changes. No main/snapshot changes, merge, deploy or live trial.

## CI proof

1. [**GitHub Actions 41215515431**](https://github.com/ment2/keenetic-vpn/actions/runs/41215515431): **SUCCESS**. The lab executed an actual **Xray 26.2.6 linux/mipsle** executable under `qemu-mipsel` on GitHub's Linux runner. Its sole parent started the child, served real SOCKS5 TCP and UDP ASSOCIATE, recorded a pending S97 `RESTART`, and was force-killed while a restarted Xray was active. The parent-death signal terminated its direct child; the driver additionally checked the old process inventory and that the port was no longer accepting connections. **Eight real independent guardian processes** then raced for the exact crashed-owner generation; one obtained a durable CAS claim. The first winner was killed, after which another eight real guardians raced to assume the exact abandoned claim; again exactly one won. On receipt reconciliation the pending restart remained **`UNCERTAIN` exactly once**, with no automatic replay. A **new direct-parent worker** then launched the restored actual MIPSLE Xray; TCP and UDP SOCKS5 checks passed. New source: `xray/lab/v30_mips_guardian_cas_recovery.py`.
2. [**GitHub Actions 41215608169**](https://github.com/ment2/keenetic-vpn/actions/runs/41215608169): **SUCCESS, 464/464** offline tests. Added cgroup v1 and no-USB rescue fault acceptance tests.
3. [**GitHub Actions 41215778116**](https://github.com/ment2/keenetic-vpn/actions/runs/41215778116): **SUCCESS, 470/470** offline tests, includes exact versioned RC5 pins, safe no-production boot layout, and publication of a review package.

**No fresh read-only or write router jobs were requested.** Prior Keenetic diagnostic `ea140581-a4db-42f5-ac4d-46c8c6c462ba` had recorded historical Linux kernel `4.9-ndm-5` and `xt_TPROXY`. This historical kernel version was not freshly reprobed.

## Linux 4.9 cgroup v1 process-containment acceptance model

`xray/lab/v30_kernel49_cgroup_v1_contract.py` is a **pure parser and logic gate**, not a cgroup controller. It accepts synthetic `/proc/cgroups`, mountinfo and two process/socket scope snapshots. Required logical conditions include:
- `pids` cgroup v1 controller present, enabled, assigned to a hierarchy, and exactly one appropriate writable cgroup v1 mount;
- dedicated process containment scope established **before any child spawn**, proof that descendants cannot escape it, and all legacy watchdog/S97/S98/S99/cron/fault-repair writers fenced;
- complete and readable `/proc` PID/start-ticks, cgroup-membership and TCP/UDP FD/socket inode inventory, two consecutive consistent snapshots and **no remaining scope members**, including renamed or reparented descendants;
- independent boot guardian outside Entware USB as a separate prerequisite.

Tests reject a missing controller, read-only or duplicated mounts, unknown process group, incomplete scans, unreadable metadata, orphaned/renamed descendants, stale PID and socket ownership, and absent guardian. Even with fully synthetic positive evidence the model returns **`OFFLINE_LOGICAL_CONTRACT_ONLY`**, never physical attestation. A cgroup `pids` controller alone does **not** seal containment or prevent a privileged member from moving itself; the scope must be independently proven unescapable. This is an important implementation gap for Linux 4.9.

## Real hardware compatibility acceptance matrix

| Requirement | Disposable evidence | Physical Keenetic 4.9 status | Release decision |
| --- | --- | --- | --- |
| `pidfd_open`, `pidfd_send_signal` | Excluded from new direct-parent lab | Linux 4.9 lacks these syscalls | **Unsupported, never use** |
| `PR_SET_PDEATHSIG`, `waitid(WNOWAIT)`, sole-reaper ownership | Real MIPSLE Xray user-mode QEMU + host Ubuntu process tests | Not proven on physical 4.9/Python runtime | **NO-GO** |
| Dedicated cgroup v1 `pids` and sealed descendant scope | Synthetic parser/negative tests | Mount/controller/rights not verified on actual router | **NO-GO** |
| Exact guardian generation token and `flock` | Real 8+8 independent Linux-process CAS with real MIPSLE Xray | Unfenced old live S97/S98/watchdog/cron still present | **NO-GO** |
| Real MIPS32LE kernel TPROXY IPv4 TCP+UDP | Prior native x86 TPROXY and separate MIPS QEMU SOCKS labs | Kernel-specific real-device TCP+UDP no-leak not proven | **NO-GO** |
| Full DNS, IPv6 and kill-switch protection after crash | Existing partial historical/in-memory contracts | Current physical combined proof unavailable | **NO-GO** |
| Independent cold-boot recovery after physical Entware USB loss | Verifiable read-only archive and offline fault simulations | No proven nonUSB device, boot hook, runtime or fail-safe start | **NO-GO** |

## USB-free boot guardian blueprint, precise structure and faults

New review-only `xray/lab/v30_kernel49_nonusb_boot_rescue_contract.py` and its tests define this **proposed** tree on a genuinely separate persistent device:

```text
rescue-v30/
  manifest.json
  originals/S97.sh
  originals/S98.sh
  originals/S99.sh
  originals/watchdog.sh
  originals/wifi_rules.sh
  bin/guardian
  etc/guardian.json
  boot/boot-hook
  var/recovery.log
```

The blueprint is **not an installed executable**. It specifies exact SHA256 verification for all five RC1 frozen originals, the guardian binary and its runtime, UID/modes, verified separate mount ID and real block device, fsync and readback, recovery journal integrity, guaranteed boot order before any Xray/route mutation, and a cold boot test with USB unavailable. The executable guardian and boot hook have **not been compiled or installed**, their real device path **has not been selected**, and no physical cold-boot proof exists.

The offline model injected all of: USB missing, missing/corrupted backup, aliased same-device rescue directory, nonexecutable guardian, missing boot hook, journal write interrupted before fsync, partial file restoration, and a surviving detached descendant. Every unsafe case blocks. Even entirely positive **synthetic** flags can only yield `SYNTHETIC_CONTRACT_SATISFIED_ONLY` with `automatic_restore_authorized=false`.

## Versioned immutable review artifact and expiry

- `xray/staging/v30-kernel49-rc5-boot-rescue-review.json`, commit `4340baf8619a3ac24da5d20ec7f3301dd69ed315`, pins the Git blob SHA1 of the three new RC5 source modules, both CI runs, release gates, candidate layout, offline fault matrix and explicit no-production permissions. It refers to existing RC4 and RC1 rollback manifests.
- GitHub Actions run [**41215778116**](https://github.com/ment2/keenetic-vpn/actions/runs/41215778116) published `v30-kernel49-rc5-boot-rescue-review-NO-DEPLOY`, **artifact ID `13047960888`**, with RC5 review JSON and deterministic read-only archive of the **five exact frozen original source scripts**. The GitHub Actions artifact expires **2026-11-14**. It is not an actual bootable device, boot guardian executable, or a permanent rescue image. The source manifest in GitHub remains separately versioned.

## Next strictly safe sequence

1. **No deployment.** Freeze source and verify the full RC5 hash set, prior RC1 SHA256 five-file archive, changed guardian CAS generations, and no production trial/merge.
2. **Only an allowed and separately owner-approved read-only inventory** could assess real kernel 4.9 cgroup v1 controller and mounts, usable `prctl`/`waitid`, all S97/S98/S99/cron processes and descendants, socket inode owners, filesystem/mount ID, offUSB mount alternatives, and real kill-switch/TPROXY state. If unavailable, remain NO-GO. **Do not repeat earlier router jobs or bypass any safety tooling.**
3. Specify a reviewed, immutable **nonUSB** guardian and boot hook with independently proven executable runtime and power-loss atomic journal semantics. A pathname or Github artifact is not proof of physical independence. Cold-boot without USB needs separate explicit owner permission; this work does not authorize it.
4. Only after actual kernel-specific containment, process/drain, boot rescue, TCP+UDP TPROXY/no-leak and exact approval are proven should an individual production staged replacement be proposed. Explicitly list paths, bytes, modes, SHA256, journal/rollback and the anticipated interruption; no silent operations.

**Final gate:** **HARD_NO_GO_PRODUCTION**, despite 470/470 offline and real MIPS32LE recovery. The current physical router remains untouched and protected against unapproved changes.
