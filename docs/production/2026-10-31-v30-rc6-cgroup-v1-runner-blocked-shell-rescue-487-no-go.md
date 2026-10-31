# Keenetic Xray v30 RC6: real cgroup-v1 capability blocker, host-shell rescue rehearsal and Linux 4.9 no-change preflight

**Date:** 2026-10-31. Repository: `ment2/keenetic-vpn`. **Only branch:** `feature/xray-v30-stable-tcp-ingress-lab-20261031`.

**Release disposition: RC6 offline PASS; physical Keenetic production HARD NO-GO.** The no-router-jobs, no-main/snapshot, no-Cloudflare, no-production-firewall/routes/cron, no-merge/deploy/live-trial constraints were upheld.

## CI and exact evidence

1. **[GitHub Actions 41217255924](https://github.com/ment2/keenetic-vpn/actions/runs/41217255924): SUCCESS, 487/487 tests**, branch head `f10f743cd015aa2e2c5f61bebc5a7543d6163731`. Includes a real process executing portable host `/bin/sh` and `sha256sum` in a fresh minimal environment, exact staged archive hashes, crash at 2 of 5 script writes, corrupted-backup **zero additional writes** and recovery of **all 5/5 archived originals**.
2. **[GitHub Actions 41216829749](https://github.com/ment2/keenetic-vpn/actions/runs/41216829749): SUCCESS as a *capability probe*, actual cgroup-v1 inheritance experiment BLOCKED.** `sudo unshare --mount --propagation private` was launched on a disposable GitHub runner and attempted to mount a `pids` cgroup v1 hierarchy **inside its own mount namespace**. The kernel denied the mount; the tool reported: `CGROUP1: UNAVAILABLE kernel denied isolated cgroup v1 mount: ... none already mounted on /sys/fs/pstore`. The CI explicitly reported `CGROUP_V1_RUNNER_UNAVAILABLE_HARD_NO_GO` and **did not** claim that cgroup-v1 fork/exec inheritance or privileged escape was tested. Evidence artifact `v30-rc6-cgroup1-real-capability-evidence-NO-GO`, ID `13048181964`.
3. The actual previous real **Xray 26.2.6 linux/mipsle** + **8+8 guardian** recovery remains [**41215515431**](https://github.com/ment2/keenetic-vpn/actions/runs/41215515431) SUCCESS. **RC6 did not re-run the updated cgroup-v1 path under MIPS**, and QEMU user-mode remains distinct from Keenetic kernel 4.9.
4. The previous negative **actual detached grandchild TCP+UDP process** test [**41213319195**](https://github.com/ment2/keenetic-vpn/actions/runs/41213319195) demonstrated that `PR_SET_PDEATHSIG` only stops the direct child, not arbitrary reparented descendants. Guardian correctly refused to restart while the orphan retained its listener. These were real Linux processes, but **not enclosed in a proven cgroup-v1 namespace**.

## What was created in RC6

- `xray/lab/v30_rc6_cgroup_v1_lab.py`: disposable mount-namespace, Linux cgroup v1 `pids` capability probe; if the hierarchy is supported, forks a real process into it, observes an `exec`-ing detached grandchild inheriting membership, attempts explicit privileged movement out of the group and records either denial or a successful escape. **Both outcomes still prohibit production recovery**; denial alone does not prove a sealed group. On hosted runner the mount was denied before fork/exec; result remains **BLOCKED**. Safe cleanup is restricted to disposable descendants and temporary namespace, never production.
- `.github/workflows/xray-v30-rc6-cgroup1-lab.yml`: explicit three-attempt disposable-only runner probe; records true `CGROUP_V1_RUNNER_UNAVAILABLE_HARD_NO_GO` versus real fork inheritance if actually available, publishes evidence, never relaxes the release gate.
- `xray/lab/v30_rc6_rescue_guardian.sh`: standalone **host POSIX shell** rehearsal, no Python/Entware runtime **at restore time**. Accepts only a private disposable source+target, validates exact five original SHA256 values before any target write, denies symlinks, copies files using private temporary names and per-file rename, and rechecks all five. A controlled `V30_RC6_FAULT=after-2` exits after two copies. It deliberately does **not** write `/opt`, call router init, mutate firewall/routes/cron, or claim physical boot safety.
- `xray/lab/v30_rc6_offline_boot_rehearsal.py`: builds temporary source/target fixtures from actual frozen RC1 five-file SHA pins, launches an initial `/bin/sh` process with a fault at 2/5 replacements, simulates loss of a separate Entware USB directory, corrupts the review backup, proves refusal with no additional writes, restores the trusted bytes, and launches an **entirely fresh host shell** to complete exact 5/5 recovery. The recovered shell runs with only `PATH=/usr/bin:/bin` and no Python/Entware dependency.
- `xray/lab/v30_rc6_rescue_package.py`: deterministic non-executable USTAR archive with five exact archived original scripts, the host shell guardian, SHA256SUMS and explicit `NOT_BOOTABLE_NO_PRODUCTION_RESTORE` metadata. Every tar member is mode `0600`; the verifier rejects unsafe paths, symlinks, tampered shell/archived scripts or fake release authority.
- `xray/staging/v30-kernel49-rc6-offline-review.json`: versioned release manifest pins all four RC6 source Git blob SHA1 values, CI run IDs, previous RC5 relationship, actual cgroup-v1 mount failure and hard physical boot NO-GO flags.
- `tests/test_xray_v30_rc6_isolation_rescue.py`, `tests/test_xray_v30_rc6_rescue_package.py`, `tests/test_xray_v30_rc6_release_gate.py`: deterministic source pins, corrupted archive, symlinks/path checks, real no-Entware shell restore, and explicit physical NO-GO constraints.

**[GitHub Actions 41217255924](https://github.com/ment2/keenetic-vpn/actions/runs/41217255924) published artifact `v30-rc6-offline-host-shell-boot-review-NO-DEPLOY`, ID `13048268835`, expires November 14, 2026.** This is an auditable package, **not** an installed rescue image, not on an independently verified physical non-USB device, and not a working Keenetic boot hook.

## Linux 4.9 physical compatibility acceptance matrix (no new router jobs)

| Requirement | Evidence | Physical 4.9 status | Gate |
|---|---|---|---|
| `pidfd_open`, `pidfd_send_signal` | Linux 4.9 predates required syscalls; archive job `ea140581-a4db-42f5-ac4d-46c8c6c462ba` recorded `4.9-ndm-5` | Previous supervisor backend incompatible | **HARD NO-GO** |
| Direct parent `PR_SET_PDEATHSIG`, `waitid(WNOWAIT)`, PID-reserved child | Real MIPSLE Xray on Ubuntu-host QEMU | Physical Keenetic kernel, Entware Python and Xray descendants unverified | **NO-GO** |
| Cgroup v1 pids controller and **unescapable** sealed membership | RC6 real GitHub runner attempted mount and was denied; earlier synthetic checks only | Unknown real controller, mount ID, privileges and escape prevention | **NO-GO** |
| Complete old S97/S98/S99/watchdog/cron and orphan inventory | Negative real detached TCP+UDP orphan lab, model double scans | Real legacy writers, PID ticks and all FD/socket inode owners not inventoried | **NO-GO** |
| Xray kernel TCP+UDP TPROXY, DNS, IPv6, kill-switch | Native x86 TPROXY only plus separate MIPS SOCKS5 evidence | Not jointly proven on physical 4.9 | **NO-GO** |
| Boot rescue without physical Entware USB | Independent **host shell process** on simulated path; 5/5 SHA matches | No verified separate block device, boot order, executable guardian/runtime or cold-boot/power-loss | **NO-GO** |

**Important:** A `pids` cgroup v1 controller can limit forks but does not by itself guarantee that a privileged process cannot migrate out of its group, or that all existing legacy writers were contained before spawning. A successful mount and two identical `/proc` scans would not establish this property. Kernel/permissions/namespace/escape verification and unowned sockets remain independent requirements.

## Explicit read-only preflight evidence plan (NOT EXECUTED)

All observations would require **separate explicit permission** and an allowed read-only connector operation. No `exec` workaround to previous policy-blocked router jobs, no repeated job IDs, no reinstall or process signal.

1. **Kernel and controller:** read the actual `uname -r`, `/proc/cgroups` (especially pids hierarchy), `/proc/self/mountinfo`, `/proc/<pid>/cgroup`, permissions of the relevant existing cgroup directories. Compare with the archived `4.9-ndm-5`; never infer capabilities from Python version.
2. **Full legacy service/writer inventory:** read current on-disk S97/S98/S99/watchdog and cron entries, current `/proc/<pid>/stat` PPID, state, start ticks, `cmdline`, `exe`, cgroup and task/thread identities, all reparented/detached descendants. Stop if unreadable, unfenced or any identity changes.
3. **Sockets and routing state:** read `/proc/net/tcp`, `udp`, `tcp6`, `udp6` and PID FD socket inodes to map all listeners; review existing TPROXY/killswitch/fwmark/table100 status **without modifying them**. No PID-only kill or automatic restarting.
4. **Physical mounts:** read `mountinfo` major:minor, source, and actual persistent storage medium for any proposed rescue, plus boot-stage process readiness and executable/runtime availability without USB. A second directory on the Entware flash drive does not qualify.
5. **Release gate:** compare actual SHA256 of working `config.json`, Xray, old canary and five frozen scripts with archived pins; require owner-approved exact new paths/bytes/modes and fully proven rollback/out-of-USB boot mechanism **before** any live operation.

The previous read-only `/proc/sys/kernel/osrelease` job `6e65e44d-3f82-4ba9-89a5-f5ac64e47d3b` failed; it was **not** repeated or bypassed in this stage.

## Scope/decision

- **PASS:** 487 offline tests, deterministic no-deploy tar, process crash at 2/5, corrupted source no-write, exact 5/5 restoration through a fresh host `/bin/sh`, metadata+SHA immutability, no production writes.
- **BLOCKED (truthful):** real cgroup v1 fork/exec/escape experiment on the available GitHub runner, because kernel denied the mount. The workflow's SUCCESS means correct capability diagnosis and evidence artifact, **not** successful group isolation.
- **NOT TESTED PHYSICALLY:** cold boot with USB removed, true nonUSB durable rescue, real Linux 4.9 process containment, full physical MIPS kernel TPROXY/DNS/IPv6/fail-closed and integrated live migration.

**RELEASE: HARD_NO_GO_PRODUCTION.** No new Keenetic router jobs, no Cloudflare, main/snapshot, Xray/cron/firewall/routes, merge/deploy or live trial. RC6 can be reviewed and tested further on a separate disposable runner or explicit VM with real cgroup v1 kernel support; no router activity is authorized.
