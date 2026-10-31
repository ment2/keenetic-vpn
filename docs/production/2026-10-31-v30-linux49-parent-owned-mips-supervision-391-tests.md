# Keenetic Xray v30: Linux 4.9 parent-owned supervision, real MIPSLE crash recovery and RC1 release gate

Date: **2026-10-31**. Repository `ment2/keenetic-vpn`. **Feature branch only:** `feature/xray-v30-stable-tcp-ingress-lab-20261031`. No merge, deploy or production/Cloudflare/router changes.

## Completed and independently confirmed

- [**GitHub Actions 41211906271**](https://github.com/ment2/keenetic-vpn/actions/runs/41211906271): **SUCCESS** on commit `8a2c9ae3499f709e13944945ed222a5a10566a0b`. Real official **Xray 26.2.6 linux/mipsle** was executed via `qemu-mipsel` on disposable Ubuntu runner. In each of four cases, the parent-owned candidate child was stopped/killed, and a **fresh independent guardian** started and owned a restored old-generation real MIPSLE Xray. SOCKS5 **TCP and UDP ASSOCIATE** end-to-end tests passed for the restored service:
  1. `parent_crash`: SIGKILL the only Python parent supervisor while its child MIPSLE Xray runs. Child receives `PR_SET_PDEATHSIG=SIGKILL`, and new guardian restores old service without signalling its historical PID.
  2. `child_exit`: the **direct owning parent** sends SIGTERM, confirms the child is **unreaped** with `waitid(P_PID, WEXITED|WNOHANG|WNOWAIT)`, then reaps only its child. Recovery independent.
  3. `rollback`: the owning parent durably writes rollback intent, sends PID-scoped SIGTERM to its **own** child and is killed before completing rollback; a fresh guardian restores old generation.
  4. `prepared`: the owning parent is killed **after fsynced PID/start-ticks journal** but **before releasing the child exec gate**; child's pipe EOF and parent-death signal prevent an unidentified Xray from starting, then the guardian restores old generation.
- [**GitHub Actions 41212083013**](https://github.com/ment2/keenetic-vpn/actions/runs/41212083013): **SUCCESS, 391/391 offline unit/contract tests** on commit `a060694ccff2e2050ea18ca41a828e34db502e4c`. This includes previous 375/375 contracts, new direct-parent `WNOWAIT` child-PID reservation tests, fsync/exec error cases, no-orphan-signal assertions, and versioned RC2 lab-contract integrity.
- Prior native x86 Linux namespace TPROXY CI [41209311676](https://github.com/ment2/keenetic-vpn/actions/runs/41209311676): SUCCESS x3 TCP/UDP with fail-closed, but **NOT MIPS kernel TPROXY**.
- Earlier MIPS32LE QEMU TPROXY experiments failed with `IP_TRANSPARENT > protocol not available` in user-mode syscall translation, which is **not fixed by this parent-child supervision lab**.

## Exact new files, Git blob SHA (not SHA256)

| File | Git blob SHA1 |
| --- | --- |
| `xray/lab/v30_parent_owned_kernel49.py` | `39870202391bfdfce4494de1d1bc823daf89a966` |
| `xray/lab/v30_parent_owned_mips_recovery.py` | `8b0de30cf648cb3e9343818dc6830897d3bf4884` |
| `tests/test_xray_v30_parent_owned_kernel49.py` | `688d7015d4d8a6fbb43544fbe7331aad99ba920b` |
| `xray/staging/v30-parent-owned-kernel49-lab-spec-v1.json` | self-contained versioned spec; above blob ids are checked by `tests/test_xray_v30_parent_owned_release_spec.py` |

The versioned spec explicitly pairs with `xray/staging/v30-release-manifest-v1.json` and `xray/staging/v30-rescue-contract-v1.json`, preserves the archive hash pins for S97/S98/S99/watchdog/wifi-rules, and sets **`LAB_ONLY_NOT_INSTALLABLE`**, `deploy_authorized=false`, `cutover_authorized=false`, `router_commands=[]`.

## Why this avoids the Linux 4.9 PID-reuse race (under the proven assumptions)

`pidfd_open` (Linux >=5.3) and `pidfd_send_signal` (>=5.1) cannot work on the archived Keenetic kernel **`4.9-ndm-5`**, historical read-only job `ea140581-a4db-42f5-ac4d-46c8c6c462ba`; this historical version was NOT checked again.

The new laboratory prototype **never signals a journal PID from another guardian**. When one dedicated single-threaded supervisor owns the direct foreground Xray child, its PID cannot be reused until that parent reaps it. Using `waitid(...WNOWAIT)` to observe child termination **without reaping** preserves this kernel reservation. `os.kill(child.pid,...)` is permitted **only to that parent's unreaped direct child**, after checking the child's PPID, start-ticks, and ownership. `SIGCHLD=SIG_IGN` is rejected, and the intended production design must additionally exclude `SA_NOCLDWAIT`, concurrent wait/reap threads and other code that reaps the child.

The child itself sets `PR_SET_PDEATHSIG=SIGKILL` in the forked process **before** `execv`, checks it still has the expected parent, and remains blocked on a one-byte pipe until the parent fsyncs its candidate PID/start-ticks journal. On parent death before exec, pipe EOF means **no Xray launch**; on parent death after exec, PDEATHSIG kills the foreground child. **Xray fork/daemonizing or spawning independent descendants would violate this proof** and needs dedicated tests and an explicit block.

## Recovery and boot/rescue boundaries

- Under `qemu-mipsel` the disposable guardian waited for candidate PID/start-ticks to disappear and for old-generation SOCKS5 TCP and UDP ownership to be relinquished before launching the new owned Xray. **It never killed an unowned PID**, even if that PID was recorded in the journal. If identity or liveness is ambiguous, the design fails closed rather than targeting a potentially recycled PID.
- The RC1 five-script rollback remains versioned and unchanged, with SHA256/0755 archive pins and a missing/corrupted backup **NO-WRITE** invariant.
- `xray/lab/v30_outofusb_mount_gate.py` continues to require a **physically distinct** persistent rescue device, boot access, usable guardian executable without Entware USB, cold-boot evidence, SHA validation and owner approval. The earlier recovery of five scripts from a different directory on a disposable runner **did not** establish actual independent storage on Keenetic.
- Re-running the standalone Python guardian after killing supervisor demonstrates **process-restart/journal recovery**, not boot ROM, cold reboot, storage loss, power loss, kernel 4.9 device behavior, or actual IPv4/IPv6/DNS VPN fail-closed.

## Unresolved **production hard blockers**

1. **This is LAB code, not the deployed S97/S98/S99 supervisor.** Need integrate parent-owned process lifecycle into reviewed cooperative broker/canary plus unchanged live kill-switch/route and 30/60-second watchdog/Wi-Fi/cron contracts. The currently staged `v30_supervisor_core.py` still requires pidfd and is **incompatible with 4.9**; do not pair it with real service wrappers.
2. **Kernel 4.9 physical proof missing.** QEMU user-mode MIPSLE ran on Ubuntu host kernel (not Keenetic 4.9); real availability and precise behavior of `PR_SET_PDEATHSIG`, `waitid(WNOWAIT)`, Entware Python and Xray fork/child tree require separate non-disruptive review and approved testing.
3. **Independent durable USB-free boot recovery not proven.** Root-only 0700 on a different directory on the same USB is not an independent rescue. No verified hardware mount/out-of-USB boot guardian exists.
4. **Real MIPS kernel TPROXY TCP/UDP and VPN/DNS/IPv6 leak checks missing.** Existing native x86 TPROXY and MIPS QEMU SOCKS results are independent, not a combined proof.
5. **Exact-file approval:** production replacement requires separate owner approval of all paths, full source hashes, backup/rollback and a validated out-of-band control path after all release gates pass.

**Decision:** PASS Linux-4.9-compatible **ownership concept on disposable runner** with real MIPSLE process, including four crash classes. **NO-GO production staging/merge/trial.** No new Keenetic jobs, Xray signals, firewall/routes/cron, Cloudflare, main/snapshot or live changes. Preserve original installed canary SHA256 `8e57ef5054f53174a35d906d34eab073dd6d787607cb02f29d83364ae3abc203`.

## Next continuation

Build a **single-parent, sole-reaper foreground Xray lifecycle service** as staging-only candidate with a single existing shared `flock` and a separate no-USB guardian design. Probe Linux 4.9-only semantics via externally authorized read-only channels if supported; do **not** bypass previous safety blocks or duplicate router jobs. Add nested-child/process-group and concurrent cron/S98 migration fault tests, plus hardware rescue constraints. Only propose exact-file production install after tests and owner consent.
