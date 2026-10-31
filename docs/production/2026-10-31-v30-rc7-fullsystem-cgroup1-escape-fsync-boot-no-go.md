# Keenetic Xray v30 RC7: actual QEMU full-system cgroup v1, privileged descendant escape, virtual power cut and offline rescue

**Date:** 2026-10-31. **Repository:** `ment2/keenetic-vpn`. **Only branch:** `feature/xray-v30-stable-tcp-ingress-lab-20261031`. **Production decision: HARD_NO_GO.**

## Independently checked CI

- [**41218961516**](https://github.com/ment2/keenetic-vpn/actions/runs/41218961516): **SUCCESS**, disposable QEMU **full-system** x86_64 VM (TCG, `Linux 6.8.0-147-generic` guest) running actual guests, **two distinct VM boots**, two 48MiB virtual ext4 rescue/active drives, and an attached simulated Entware USB image on the first boot only. QEMU process was killed using **host SIGKILL** after two of five filesystem replacements and explicit guest `fdatasync(file)`, `fsync(directory)`, and `sync`. Second full Linux boot **without the virtual USB image** recovered a durable `stage=2` journal, independently checked the five frozen RC1 original script SHA256 values, restored 5/5 exact bytes and completed. **This is a VM crash rehearsal, not an actual power-grid loss or physical Keenetic cold boot.**
- The same guest successfully mounted **actual cgroup v1 pids** within its running kernel. It executed **real `fork` + detached `setsid` + `exec`**, verified inherited `cgroup.procs`, cross-checked live TCP and UDP socket inodes against owning `/proc/<pid>/fd`, drained the descendant, and ran **two rounds of eight separate guardian processes** racing on separate file descriptions with exclusive `flock`. Exactly one lock holder won each round. **These two guest rounds are file-lock exclusivity tests, NOT a full owner-generation CAS protocol.** The prior real MIPS32LE Xray 8+8 generation-CAS remained [**41215515431**](https://github.com/ment2/keenetic-vpn/actions/runs/41215515431) SUCCESS, in separate QEMU user-mode experiments.
- **Adversarial result, not a release pass:** the privileged descendant executed a real cgroup v1 migration out of its own scope. The QEMU guest serial log explicitly recorded `RC7_GUEST: PRIVILEGED_CGROUP_ESCAPE_SUCCEEDED_HARD_NO_GO`. The `pids` controller limits process creation but is **NOT an enforced security boundary for a sufficiently privileged process that can write to parent `cgroup.procs`**. Since this escape actually succeeded, neither cgroup membership alone nor two `/proc` snapshots can prove that all Xray descendants are contained. Production remains HARD NO-GO.
- [**41219160776**](https://github.com/ment2/keenetic-vpn/actions/runs/41219160776): **SUCCESS, 494/494 offline unit/contract tests**, exact RC7 immutable Git blob SHA1 pins and explicit physical kernel/device/boot/deploy NO-GO. This supplements prior [**41217255924**](https://github.com/ment2/keenetic-vpn/actions/runs/41217255924), 487/487 offline, and the previous [**41216829749**](https://github.com/ment2/keenetic-vpn/actions/runs/41216829749) hosted-runner cgroup v1 mount **BLOCKED** probe. The new dedicated full-system guest resolved the *test environment* limitation without touching Keenetic.
- QEMU console logs and disposition: workflow artifact `v30-rc7-qemu-fullsystem-guest-and-crash-logs-NO-DEPLOY`, **ID `13048184541`**, from [run 41218961516](https://github.com/ment2/keenetic-vpn/actions/runs/41218961516), with 14-day GitHub retention. **Never** treat this artifact as the bootable rescue or actual independent storage.

## Exact new files

1. `xray/lab/rc7_fullvm_cgroup_probe.c`: statically compiled **guest-only** cgroup v1 `pids` probe with actual fork/exec + detached TCP/UDP socket creation and inode crosscheck; deliberate **privileged cgroup escape**; two groups of eight guardian flock races. No physical router or production signal is ever sent.
2. `xray/lab/rc7_fullvm_init`: minimal BusyBox static init in **full Linux kernel guest**, which mounts /proc/sysfs/devtmpfs, starts real cgroup tests, mounts distinct rescue/active virtual ext4 disks, validates SHA256, records `stage=2` on disk and stops at the explicit crash marker; on next boot without the simulated USB, confirms journal persists and restores exact originals.
3. `xray/lab/rc7_guest_fdatasync.c`: statically compiled guest helper enforcing **fdatasync(file)** and **fsync(parent dir)** on restricted `/mnt/active/` paths only.
4. `xray/lab/rc7_fullvm_runner.sh`: GitHub disposable-runner builder for matching Ubuntu generic kernel image + minimal initramfs, two raw ext4 rescue/active image files and third simulated USB image, QEMU full-system TCG; kills the first QEMU PID after durable 2/5 journal marker and boots second guest without USB. Only `RUNNER_TEMP` files are touched; no local/remote production files.
5. `.github/workflows/xray-v30-rc7-fullsystem.yml`: isolated full-system CI job with retained guest console logs; checks actual cgroup/FD/proc and 8x2 flock markers when available, fails if an experiment fails after cgroup mount instead of reporting false success, and always states physical NO-GO.
6. `xray/staging/v30-rc7-fullsystem-review.json`: RC7 versioned evidence with **exact Git blobs** of five sources, run IDs, real-guest `privileged_descendant_escaped_cgroup_v1:true`, virtual rescue disk constraints and **zero production approval**.
7. `tests/test_xray_v30_rc7_fullsystem_review.py`: exact Git SHA1 source pins, guest vs physical distinction, privileged-escape **NO-GO**, virtual vs physical power-cut distinction and explicit no-production-gate checks.

## Linux 4.9 / actual Keenetic acceptance matrix

| Property | Evidence in this stage | Physical Keenetic | Release gate |
| --- | --- | --- | --- |
| cgroup v1 pids mount, fork/exec, detached member | **PASS inside full QEMU guest Linux 6.8** | Actual historical Keenetic `4.9-ndm-5` support/permissions unknown | **NO-GO** |
| Privileged descendant cannot escape scope | **FAIL: actual escape succeeded** in guest | No kernel-enforced closed scope proven on real 4.9 | **HARD NO-GO** |
| PID/start-ticks, socket TCP+UDP FD-inode owners | **PASS in guest test process** | No complete current inventory of all Xray/cron/watchdog/legacy writers | **NO-GO** |
| Guardian lock exclusivity | **PASS 8+8 separate guest processes** | Installed legacy entrypoints still do not share new lock | **NO-GO** |
| Full owner-generation guardian CAS with real MIPS32LE Xray | Previously **PASS** with Xray 26.2.6 under **QEMU user-mode, host Linux kernel** | Not demonstrated on physical MIPS kernel 4.9 | **NO-GO** |
| Power-cut, journal/recovery across boots | **PASS VM QEMU SIGKILL + reboot, ext4 virtual disks, fdatasync/fsync** | Real power loss, flash hardware, actual boot hook and independent permanent nonUSB rescue untested | **NO-GO** |
| Kernel TPROXY TCP+UDP / DNS IPv6 no-leak / kill-switch | Earlier x86 native TPROXY and separate MIPS SOCKS5 evidence | Full real 4.9 packet/routing safety not proven | **NO-GO** |

Historical Keenetic read-only job `ea140581-a4db-42f5-ac4d-46c8c6c462ba` recorded `4.9-ndm-5` and `xt_TPROXY`; this job was **not repeated** and no router jobs were submitted. The original pidfd supervisor still cannot work on kernel 4.9.

## Safety and next physical gate

A viable production design must first **deny privilege to all confined Xray descendants in a way that prevents any unreviewed cgroup migration**, or provide a different proven kernel-enforced process containment strategy on the actual Keenetic. Just creating a `pids` cgroup and scanning twice is demonstrably unsafe in the real guest. Must also fence legacy S97/S98/S99/wifi/watchdog/cron entrypoints and all detached processes, and prove the supervisor/boot guardian can execute and restore from an independently persistent **physical** medium without Entware USB.

The physical preflight is **read-only and requires a separately approved authorized source**: gather current `uname -r`, `/proc/cgroups`, `/proc/self/mountinfo`, actual relevant controller directories and `cgroup.procs`, legacy init+cron, complete `/proc/<pid>/stat`, cmdline/exe, socket FD inode mapping `/proc/net/{tcp,tcp6,udp,udp6}`, physical mount sources and candidate rescue boot order. Any missing/forbidden read => NO-GO, no bypasses, no repeat jobs. For power-loss and USB removal, separate exact-file+device owner consent and out-of-band management proof are mandatory and **not covered** here.

**Production unchanged:** no Keenetic commands/jobs or signals; no installed Xray, firewall, routes, kill-switch, cron, Cloudflare, main/snapshot, merge, deploy, trial or automatic rollback. All RC7 code and artifacts are only on the feature branch/disposable GitHub runners.
