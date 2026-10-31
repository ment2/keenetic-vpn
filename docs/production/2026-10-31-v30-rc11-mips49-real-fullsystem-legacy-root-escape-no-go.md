# Keenetic Xray v30 RC11: real MIPS32LE Linux 4.9 full-system, cgroup v1 privileged escape, legacy/boot hardware NO-GO

**Date:** 2026-10-31. **Repository:** `ment2/keenetic-vpn`. **Only target:** `feature/xray-v30-stable-tcp-ingress-lab-20261031`. **No production authority:** new router jobs=0, Cloudflare/production/main/snapshot/firewall/routes/cron/merge/deploy/live trial none.

## 1. Critical finding: genuine MIPS32LE Linux 4.9, not user-mode

[**Full-system MIPS32LE Linux4.9 CI 41226245794**](https://github.com/ment2/keenetic-vpn/actions/runs/41226245794) **SUCCESS**. Actual **QEMU system-mipsel**, `-M malta -cpu 4KEc -net none`, guest kernel `4.9.0-13-4kc-malta`, official Xray **26.2.6 linux/mips32le**. The MIPS guest owns its own kernel, procfs, syscalls, cgroups, real PID namespace and sockets. It is not `qemu-mipsel` user-mode running under GitHub's x86 kernel. The exact QEMU serial trace was downloaded and inspected from [Actions artifact **13051534522**](https://github.com/ment2/keenetic-vpn/actions/runs/41226245794).

Independent [**archive discovery CI 41225710199**](https://github.com/ment2/keenetic-vpn/actions/runs/41225710199) **SUCCESS** retrieved binaries but did **not** execute them. Main full-system workflow executes the kernel and executable **only after enforcing all four SHA256**:

| Input | SHA256 |
|---|---|
| Archived Debian `linux-image-4.9.0-13-4kc-malta_4.9.228-1_mipsel.deb` | `9a5dff9c498bf5736ca9f97cbb005b4b60bd139aa0f30f5bab9feca783907d9b` |
| `vmlinux-4.9.0-13-4kc-malta` MIPS32LE | `20f5380e02f2e40d4495fd61a854e5867f5ccdf95c8c1fd3d53fe27e8be1797f` |
| Official `Xray-linux-mips32le.zip` v26.2.6 | `1590b2bcefe64fb0604f29c8c75219bfbe8f63daa3bc8e3956edfa6da97c5869` |
| Extracted `xray` MIPS32LE ELF | `3d2588c5ef770a6a7e1bfdd5db511130fb3acd79eb91bfcb108753b3e1dda1f6` |

Hashes pin reproducible bytes; a separately validated publisher signature was **not** established.

## 2. Real MIPS kernel evidence

The downloaded actual guest serial log contains these verified results:

1. `uname=4.9.0-13-4kc-malta arch=mips`; the MIPS process independently called `PR_GET_NO_NEW_PRIVS` **after exec** and got `1`.
2. With UID/GID **65534** and **no effective capability**, real TCP and UDP `setsockopt(IP_TRANSPARENT)` were both refused.
3. With UID/GID **65534** and **only effective `CAP_NET_RAW`** (`CapEff=0x2000`), both TCP and UDP `IP_TRANSPARENT` succeeded. Real official MIPS32LE Xray 26.2.6 then opened its isolated TCP+UDP transparent-mode inbound on port 12345. Parent pinned actual child PID/start-ticks, signalled **only its own direct unreaped child**, waited it and proved listener drain. No broadcast signals or global killall.
4. Real **cgroup v1 `pids` mounted**; root-owned child performed `fork/setsid/exec`, acquired TCP and UDP FD/socket inode and **successfully migrated to the parent cgroup**. Guest output exactly `PRIVILEGED_CGROUP_ESCAPE_SUCCEEDED_HARD_NO_GO`. **This disproves any assumption that cgroup v1 alone seals privileged legacy descendants on actual MIPS Linux 4.9.**
5. The eight independent **unprivileged** `fork/setsid/exec` children were denied cgroup escape and verified to remain members. An unknown reparented grandchild correctly held `GUARDIAN_DENIES_RESTART_UNKNOWN_REPARENTED_DESCENDANT` until membership drained.
6. Exactly **one winner in each of three actual waves of eight competing guardians**, guarded by a separate `flock`, atomic generation journal and fsync. A guardian was SIGKILLed after fsynced PREPARED but before commit; the ledger **did not advance** and new guardians completed the next generation once.

**Boundary:** these are full guest MIPS Linux4.9 tests, but Debian Malta hardware is *not* Keenetic Ultra KN-1810 or its vendor `4.9-ndm-5` and does not prove installed S97/S98/S99 or production watchdog integration.

## 3. Exact MIPS full TCP/UDP TPROXY packet path: not proven

Guest boot intentionally ran with **`-net none`**: there is no external ingress interface, no emulated inter-namespace Ethernet link, no guest-installed MIPS `iptables xt_TPROXY` rules or corresponding `fwmark`/policy-route table. Actual full TCP/UDP **packet forwarding via MIPS Linux4.9 TPROXY therefore was NOT executed**, despite a real `IP_TRANSPARENT` syscall and genuine Xray listener. Claiming it has passed would be false.

The separately verified [**native Linux netns 41224152158**](https://github.com/ment2/keenetic-vpn/actions/runs/41224152158) did prove a complete synthetic TCP/UDP packet path through real `iptables TPROXY`, marked routing and no direct fallback, **on the GitHub runner's x86_64 kernel, not MIPS Linux4.9**.

**Precise next isolated acceptance:** create 2-3 independent emulated NIC/guest hosts, pin valid MIPS32LE `xt_TPROXY`/socket modules and `iptables`/route tooling compatible with Malta Linux4.9, install guest-only rules, verify actual packet bytes + kernel counters for both TCP and UDP, test Xray crash with no alternative route, IPv6/DNS and CAS rollback. No cross-kernel "PASS" substitution.

## 4. RC11 hard-gate for all seven legacy spawning surfaces

`xray/lab/rc11_privileged_legacy_fencing_contract.py` is an **offline evidence verifier**, not a router command runner. It enumerates exact archived legacy actors: `S97xray`, `S98xray-wifi`, `S99xray-watchdog`, `xray-watchdog.sh`, `xray-wifi-rules.sh`, `xray-fc-cron-guard.sh` and `xray-safe-hourly.sh`.

The verifier demands exact archived hashes where known; separate acknowledgments from **boot, cron and active subprocess entrypoints under shared flock**; sealed-before-first-spawn cgroup membership; actual independent kernel capability boundary; no privileged escape; all orphan descendants drained; complete socket-inode visibility; matching boot UUID and PID/start-ticks; exact guardian generation; journal PREPARED-not-COMMITTED recovery; physically independent rescue proof; and live SHA attestation. Missing, duplicate, stale, PID-reused, root/privileged, or out-of-scope entries cause explicit **HARD_NO_GO**. Even synthetic all-true evidence is **OFFLINE_REVIEW_CANDIDATE_ONLY**, with `deployment_authorized:false`. The 16 test methods systematically exercise these refusals.

No production actor has been fenced or disabled. The guest's observed root cgroup escape explicitly means **physical migration is not authorized**.

## 5. Versioned rescue and real hardware acceptance

Existing [RC10 Linux4.9 full-system CI **41224765496**](https://github.com/ment2/keenetic-vpn/actions/runs/41224765496) remains **SUCCESS**: three two-boot QEMU virtual ext4 scenarios after host SIGKILL at 2/5 fsynced file changes: clean 5/5 rollback, blank rescue refusal with zero additional writes, and **entirely detached virtual rescue device** refusal with zero additional writes. This does not reproduce electrical power loss or prove distinct physical storage.

The new `xray/lab/rc11_hardware_boot_rescue_gate.py` extends the independent mount verifier with: disjoint mount/device/source; independent **physical power domain**; actual USB-unplugged cold boot; guardian starts before cron; root ownership 0700; five SHA256 originals; file and parent-dir fsync; committed journal sequence; corruption of journal/source must not write; interrupted rollback exact replay; unknown child fenced; physical vendor NDM5 evaluation. Its tests fail closed if any individual witness is missing or both mounts refer to the same disk. Review-only; nothing is installed.

**Physical blocker:** not a single one of these physical Keenetic attestation gates has been completed by the QEMU tests. There is no authorized router read-only preflight, reboot, independent rescue disk, failover trial or owner-approved exact production file cutover in RC11.

## 6. Sources, versioning and decision

New read-only/disposable sources:
- `xray/lab/rc11_mips49_guest_init.c`
- `xray/lab/rc11_mips49_fullsystem_runner.sh`
- `xray/lab/rc11_privileged_legacy_fencing_contract.py`
- `xray/lab/rc11_hardware_boot_rescue_gate.py`
- `.github/workflows/xray-v30-rc11-mips49-discovery.yml`
- `.github/workflows/xray-v30-rc11-mips49-fullsystem.yml`
- `tests/test_xray_v30_rc11_legacy_fencing.py`, `tests/test_xray_v30_rc11_hardware_boot_rescue.py`, `tests/test_xray_v30_rc11_mips49_release.py`
- `xray/staging/v30-rc11-mips49-fullsystem-legacy-fencing-review.json` pins **eight** exact Git source blobs, all four MIPS archive/executable hashes, CI evidence and explicit hardware negatives.

**Release disposition: RC11 MIPS32LE FULL-SYSTEM LAB PASS, PRODUCTION HARD NO-GO.** GitHub feature branch and disposable runner only. No new Keenetic jobs or bypass of blocked tools, no actual Xray/Cloudflare/cron/firewall/routes/kill-switch modifications, no `main`/`snapshot` edits, no merge/deploy/live trial.
