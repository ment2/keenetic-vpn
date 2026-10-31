# RC17–RC21: MIPS32LE Linux 4.9 userland, real xt_TPROXY packet path, official Xray integration and physical HARD NO-GO

**Date:** 2026-10-31. **Branch:** `feature/xray-v30-stable-tcp-ingress-lab-20261031`. Baseline `db555928a7087490cd9d72c896af779f1589c763`. **No real Keenetic jobs or production access**. This is a status/evidence report, not a deployment authorization.

## Verified archived Debian Stretch MIPS32LE package SHA256s

| Package | SHA256 |
|---|---|
| `iptables_1.6.0+snapshot20161117-6_mipsel.deb` | `b0bd6d7e4bc7da38672b223cb428315309979a19e008aedafb17253315178b67` |
| `iproute2_4.9.0-1+deb9u1_mipsel.deb` | `c0b0886583db81db0a517e0945be52d23dcc3ee5fe8ea068bfdaa80cb639213d` |
| `busybox-static_1.22.0-19+b3_mipsel.deb` | `0c7e287104914e654a2555e9900302180ff54d1ef17e9faf585529e6eadac8e0` |
| `libc6_2.24-11+deb9u4_mipsel.deb` | `5515fb37ad178bb61b5ce53e0d36860d865779174352403ee7ed20976777f129` |
| `libip4tc0_1.6.0+snapshot20161117-6_mipsel.deb` | `f2182182b5a4834c7cb81cbedb8666731c0de8368cf53b9a908d58dca9369db8` |
| `libip6tc0_1.6.0+snapshot20161117-6_mipsel.deb` | `80b61d515779bc62fbbac799d5d5fbe102f97f860d4ec11a42ca3dc4f3c3f820` |
| `libxtables12_1.6.0+snapshot20161117-6_mipsel.deb` | `d820b1df1df638a5d2682a827f06c7e4032546da786db2f714bf70b1dad0937b` |

Guest Debian Linux `4.9.0-13-4kc-malta`: .deb SHA256 `9a5dff9c498bf5736ca9f97cbb005b4b60bd139aa0f30f5bab9feca783907d9b`, vmlinux SHA256 `20f5380e02f2e40d4495fd61a854e5867f5ccdf95c8c1fd3d53fe27e8be1797f`. Official Xray 26.2.6 MIPS32LE ZIP `1590b2bcefe64fb0604f29c8c75219bfbe8f63daa3bc8e3956edfa6da97c5869`; executable `3d2588c5ef770a6a7e1bfdd5db511130fb3acd79eb91bfcb108753b3e1dda1f6`.

## CI findings, each with exact scope

1. **RC17 archive discovery** [41231145019](https://github.com/ment2/keenetic-vpn/actions/runs/41231145019) **SUCCESS**: all `ld.so.1`, `libc`, `libdl`, `libm`, `libip4tc`, `libip6tc`, `libxtables` exist in archived MIPS packages, with SHA and symlink metadata. Static only.
2. **RC18 actual QEMU MIPS userland** [41231297244](https://github.com/ment2/keenetic-vpn/actions/runs/41231297244) **SUCCESS**: SHA-check *all seven* packages; actual full-system QEMU MIPS Linux4.9 loads `xt_TPROXY` and executes real MIPS `/bin/ip -V`, `/sbin/iptables -V`, `iptables -t mangle -L -n`. Dependency closure executable. `-net none`; no packets.
3. **RC19 real isolated NIC** [41231656175](https://github.com/ment2/keenetic-vpn/actions/runs/41231656175) **FAILURE** with positive partial witness: QEMU PCnet, host↔guest TCP exact 25 bytes; guest UDP backend *received* exact 25 bytes; host UDP-return timed out **six** times with SLIRP `restrict=on`. Do not call bidirectional UDP successful.
4. **RC20 MIPS kernel xt_TPROXY** [41232045208](https://github.com/ment2/keenetic-vpn/actions/runs/41232045208), final rereun [41232197650](https://github.com/ment2/keenetic-vpn/actions/runs/41232197650) **SUCCESS**: guests load `xt_TPROXY`, `xt_tcpudp`, `xt_socket`, `iptable_mangle`, `pcnet32`; real guest-only mangle PREROUTING TCP/UDP TPROXY rules, `fwmark` policy rule/local route; **real TCP host echo** and **guest TCP/UDP byte-equal receipts** at transparent test sockets, positive TCP/UDP netfilter packet counters. **Not Xray**. Host UDP return still unproven.
5. **RC21 actual official MIPS Xray**: [41232671856](https://github.com/ment2/keenetic-vpn/actions/runs/41232671856) **FAILURE**, yet concrete positive evidence: official binary starts in real MIPS Linux4.9, UID 65534, `CapEff=0x2000` (`CAP_NET_RAW` only), capwrap successful `PR_SET_NO_NEW_PRIVS` before exec, Xray TCP/UDP listeners, actual TCP TPROXY packet passed through Xray to guest backend and host returned 25 matching bytes. **UDP through Xray to backend/host NOT confirmed**; host UDP return timed out; backend did not complete before QEMU deadline. Next diagnostics [41232946352](https://github.com/ment2/keenetic-vpn/actions/runs/41232946352) **FAILURE** due bounded host readiness check before Xray marker; subsequently raised disposable readiness window at `8e15cfa7` for clearer classification. Never relabel failures as success.
6. **Offline fail-closed review** [41232776878](https://github.com/ment2/keenetic-vpn/actions/runs/41232776878) **SUCCESS, 578/578 tests** at `bc37ea4f`. `rc20_packet_release_gate.py` rejects each of 21 missing witnesses: true TCP/UDP both ways, real Xray both protocols, no bypass/no DNS/IPv6 leak, seven exact legacy spawners inhibited, privileged root cgroup escape independently fenced, PID/start ticks/socket inode/generation CAS, vendor kernel, independent physical USB-absent cold boot/rescue, exact SHA and crash/fsync rollback. Synthetic all-true **cannot** set production authorization or assert real packet proof.

## Blocking risks independent of CI

- **MIPS Xray UDP backend and return:** not demonstrated; actual RC21 evidence has only TCP via Xray. QEMU user networking `restrict=on`, no external access. No relaxation of isolation, no fabricated green result.
- **No-fallback/no-leak:** no demonstrated denial of direct egress after Xray crash on *MIPS4.9* and no complete DNS/IPv6 packet isolation proof. x86 native results never substitute for MIPS kernel.
- **Privileged legacy process fencing:** RC11 **observed actual successful root descendant escape from cgroup v1**. Cooperative flock, descendants/PID scans, generation CAS without kernel/pre-boot enforcement cannot close seven S97/S98/S99/watchdog/Wi-Fi/cron entry points. No production spawner inhibition can be claimed.
- **USB-independent boot/rescue:** no physical separate power domain, USB-detached true cold-boot guardian, atomic original-five exact SHA restoration, interrupted fsync/journal recovery and vendor `4.9-ndm-5` hardware. Disposable QEMU proof is not physical certification.

**Disposition: RC17/18/20 SUCCESS in their bounded lab scopes; RC19 and RC21 remain FAIL and must not be presented as full acceptance. Production = HARD_NO_GO_PRODUCTION.** Absolutely no Keenetic jobs, production/main/snapshot/Cloudflare/real firewall/routes/cron/merge/deploy/live trial.
## RC21 final pinned UDP bind-conflict evidence (CI 41233279539)

The final disposable [RC21 run 41233279539](https://github.com/ment2/keenetic-vpn/actions/runs/41233279539) at source commit `6ab7d13fa86ff9d8c192b43b8552d62b87525358` completed **FAILURE**, correctly preserving HARD NO-GO. This version prints real in-guest `iptables -t mangle -xvnL PREROUTING` counters and actual Xray debug lines:

- TCP TPROXY: **6 packets / 269 bytes**. Host received exact **25-byte TCP echo** through real official Xray MIPS32LE and backend.
- UDP TPROXY: **3 packets / 159 bytes**. Xray reports original UDP destination `udp:10.0.2.15:19191`, so Linux Netfilter *did* redirect UDP and Xray *did* observe it.
- Xray: `app/proxyman/inbound: connection ends > fake: socket bind: address already in use` **on each of three UDP attempts**. Guest backend did not receive UDP; host did not receive UDP reply.
- This lab places the backend UDP listener on the **same guest IP and original destination port**. Binding collision is the strong topology hypothesis, but independent network-namespace/backend-IP evidence is not yet available. Do not attribute this to an intrinsic MIPS Linux4.9 or Xray UDP incompatibility.
- **Precise isolated prerequisite for a future lab:** move the backend to a separate disposable L3 namespace/IP (never to router/production); preserve SHA-pinned MIPS Xray+kernel, TPROXY counter/byte evidence, exact source PID/start-ticks, fail-closed no-direct-route after crash, and IPv6/DNS no-leak. Do not remove `restrict=on` to make the test green.

**RC21 full TCP+UDP Xray acceptance FAIL; RC20 kernel-level TCP/UDP TPROXY guest PASS; physical production remains HARD_NO_GO_PRODUCTION** due additional independently observed cgroup-v1 privileged root escape and untested USB-free power-independent boot/rescue.
