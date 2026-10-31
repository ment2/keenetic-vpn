# Keenetic Xray v30: Linux 4.9 cooperative parent-owned lifecycle, real MIPS32LE, six actor entrypoints and boot/rescue RC3

**Date:** 2026-10-31. **Repository:** `ment2/keenetic-vpn`. **Only branch:** `feature/xray-v30-stable-tcp-ingress-lab-20261031`.

**STATUS:** STAGING LAB PASS. **PRODUCTION:** HARD NO-GO; router, legacy services, real cron/firewall/Cloudflare, main and snapshot remain untouched.

## Verified independent CI

- [**GitHub Actions 41213319142**](https://github.com/ment2/keenetic-vpn/actions/runs/41213319142): **SUCCESS**, a real **Xray 26.2.6 linux/mipsle binary** executed under `qemu-mipsel` with SOCKS5 TCP and UDP ASSOCIATE, and a single long-lived parent implemented the lifecycle. Multiple **concurrent external S97 requests** caused **three sequential restarts**, and the test verified continued real TCP/UDP connectivity and no two simultaneously owned Xray children. S98 may request check only (returns `DENIED` for TPROXY repair), and S99/watchdog/cron request health checks. The runner then killed the owning parent during an in-flight S97 RESTART and killed the first guardian while it held the **same filesystem flock**. A second independent guardian required proof that the old parent, direct child, known test Xray processes and TCP/UDP listener were gone; it marked the old operation `UNCERTAIN` and restored service under a **new direct parent**. It did not replay the uncertain operation nor signal any unowned PID.
- [**GitHub Actions 41213592037**](https://github.com/ment2/keenetic-vpn/actions/runs/41213592037): **SUCCESS, 411/411 offline tests**, verifying ledger generations, concurrent unique request IDs, serialized claims, owner-scoped receipts, hard stop on unknown child/owner, durable `UNCERTAIN`/non-replay, six lab-only wrappers, exact release Git blob pins, external rescue NO-GO, and orphan descendant protection.
- The standalone adversarial descendant experiment (same offline run) deliberately spawned a **detached grandchild TCP+UDP listener**. Its direct parent was killed and `PR_SET_PDEATHSIG` killed the direct child **but the grandchild survived**. The independent guardian correctly **refused** to reconcile while that process/listener remained. After the orphan **voluntarily self-exited** (no signal to stale PID), the lab-only gate permitted reconciliation. This shows why PDEATHSIG by itself is **not** a descendant-fencing mechanism.
- Earlier [**MIPS32LE parent-owned baseline 41211906271**](https://github.com/ment2/keenetic-vpn/actions/runs/41211906271) SUCCESS, four crash points: `parent_crash`, `child_exit`, `rollback` and `prepared`. Prior [**native x86 kernel-TCP/UDP TPROXY 41209311676**](https://github.com/ment2/keenetic-vpn/actions/runs/41209311676) SUCCESS x3 in disposable namespaces, **not physical MIPS kernel TPROXY**.

## New staging-only architecture

**`xray/staging/v30_kernel49_cooperative_ledger.py`** coordinates S97, S98, S99, watchdog, cron using a **single short-lived exclusive `flock` around each queue transaction**. This lock is NOT held for the entire child lifetime, which would block S98/watchdog. The ledger has sequence IDs, owner generation tokens, exclusive in-flight claims, fsynced private JSON receipts and a 24-item queue cap. Only one owner can process an operation. A crashed in-flight restart becomes **`UNCERTAIN`** and **never** automatically retries. Pending old requests are cancelled on controlled *lab-only* rescue. A stale owner is prevented from closing a quarantined ledger.

**`xray/lab/v30_kernel49_cooperative_lab.py`** exercises this protocol using the earlier parent-owned process lifecycle: the sole parent can signal its own unreaped child; outside actors **never** signal Xray, even if the journal contains its PID. Parent death uses `PR_SET_PDEATHSIG=SIGKILL`, but a new guardian still requires independent absence evidence before starting a new owner.

**`xray/lab/v30_kernel49_descendant_guard_lab.py`** is a negative test for detached descendants and reparented processes. The absence of a direct child is NOT sufficient to prove safety.

**Six staging-only shell adapters** under `xray/staging/v30_kernel49_entrypoints/`: `S97xray`, `S98xray-wifi`, `S99xray-watchdog`, `xray-watchdog.sh`, `xray-safe-hourly.sh`, and `xray-fc-cron-guard.sh`. They are **not** drop-in production scripts; they require `XRAY_V30_DISPOSABLE_ROOT` and call only a lab command that explicitly refuses production paths. S97 has START/STOP/RESTART request capability, S98 can only CHECK_TPROXY and is forbidden to modify actual iptables, and S99/watchdog/cron can only CHECK_HEALTH.

Unit/contract tests are `tests/test_xray_v30_kernel49_cooperative_ledger.py`, `tests/test_xray_v30_kernel49_entrypoints.py`, `tests/test_xray_v30_kernel49_rescue_gate.py`, alongside prior parent-owned and rescue tests. CI updates are restricted to existing `.github/workflows/xray-snapshot-contracts.yml` and `.github/workflows/xray-v30-mips32le-lab.yml`.

## Versioned RC3 boot/rescue release gate

`xray/staging/v30-kernel49-cooperative-boot-rescue-v1.json` (RC3) **pins exact Git blob SHA1 of nine immutable staging sources** (ledger, real MIPS lab, descendant trap, and six adapters). It references the unchanged RC1 original source and recovery manifests and RC2 parent-owned Xray baseline. Its CI evidence fields point to runs `41213319142` and `41213592037`.

The contract explicitly records `LAB_ONLY_NOT_DEPLOYABLE`, `production_authorized=false`, `install_authorized=false`, `automatic_reboot_recovery_authorized=false`, `merge_authorized=false`, and `router_commands=[]`. All **nine hardware rescue/boot gates remain false**. It is a *versioned specification*, not an installed boot image, not a hardware-independent rescue and not deployment authorization.

## Why Linux 4.9 production is still blocked

1. The last archived read-only Keenetic diagnostic `ea140581-a4db-42f5-ac4d-46c8c6c462ba` recorded `4.9-ndm-5`. `pidfd_open` / `pidfd_send_signal` require newer kernels. RC2/RC3 alternative uses direct-parent ownership, `waitid(...WNOWAIT)`, `waitpid` and `PR_SET_PDEATHSIG`, but **was run on Ubuntu host kernel with MIPS user-mode QEMU**, not on the physical Keenetic kernel. No new router jobs in this work.
2. **Detached descendants can survive.** The negative test explicitly demonstrates this. A real release needs strict foreground-only Xray child/process-tree verification, cancellation and orphan tracking, including all legacy cron and S97/S98 entrypoints, before any activation. It must not send `kill(pid)` to a reused/unknown PID.
3. **No validated boot rescue independent of Entware USB.** Directories on one ephemeral runner are not different physical devices. No real separate mount, cold-boot guardian executable, power-fail recovery, or USB-removed rescue is verified.
4. **No physical router VPN/TPROXY proof.** QEMU user-mode SOCKS5 TCP/UDP and x86 native kernel TPROXY are separate experiments; neither proves real MIPS kernel TPROXY, IPv6, DNS anti-leak, VPN upstream, or fail-closed route lifecycle on Keenetic.
5. **Installed canary and S97/S98/S99 still incompatible/unfenced.** The installed v30 first-cutover canary is pinned to old sources and uses a different transaction lock. Live migrations require individually reviewed exact replacement paths/byte hashes, release-level atomic install, rollback and owner approval; this staging package must **never be installed as-is**.

**Hard stop:** no production Xray changes, no new Keenetic jobs, no Cloudflare changes, no cron/firewall/route/kill-switch updates, no main/snapshot branch changes, no merge or deploy.

## Next engineering gate

Continue only in the feature branch: prove long-running parent/crash handling with nested descendants and multiple independent actor generations; design a verifiable *physical off-USB boot guardian* with immutable rescue artifacts (without installing it); integrate actual kernel 4.9 capability and full legacy-actor process inventory only through permitted read-only channels. Until these gates and an explicit file-by-file owner approval, **production remains NO-GO**.
