# RC23: independently falsified positive UDP hostfwd return under restrict=on; exact original destination remains HARD NO-GO

**Date:** 2026-10-31
**Repository:** `ment2/keenetic-vpn`
**Feature branch only:** `feature/xray-v30-stable-tcp-ingress-lab-20261031`
**Production:** `HARD_NO_GO_PRODUCTION` (not a deployment request, no router operations).

## Verified GitHub Actions outcomes

| Run / commit scope | Result | Exact meaning |
|---|---|---|
| [41235004868](https://github.com/ment2/keenetic-vpn/actions/runs/41235004868), commit `0449e0afb2` | **FAILURE, exit 4** | Isolated Linux4.9 MIPS32LE QEMU *without Xray and without TPROXY* did not deliver a single UDP reply to host through loopback-only SLIRP `hostfwd=udp`, despite guest receive/sendto |
| [41234991915](https://github.com/ment2/keenetic-vpn/actions/runs/41234991915) | SUCCESS | Earlier offline contracts |
| [41235136040](https://github.com/ment2/keenetic-vpn/actions/runs/41235136040), commit `b63496106c` | **SUCCESS, 607/607 offline tests** | Includes strict original-destination/independent-UDP evidence mutation tests. No packet proof or hardware authorization |
| [41233646934](https://github.com/ment2/keenetic-vpn/actions/runs/41233646934) | SUCCESS | RC21 real MIPS `xt_TPROXY` Xray ingress TCP+UDP to redirected **guest-only** backend, does not attest original outbound or UDP host reply |
| [41234391436](https://github.com/ment2/keenetic-vpn/actions/runs/41234391436) | SUCCESS | RC22 bounded no-sentinel direct fallback after owned Xray death, not universal no-leak |

## Exact independent UDP hostfwd evidence

RC23 uses Debian MIPS32LE guest `4.9.0-13-4kc-malta`, SHA256 pinned archive and modules, QEMU PCnet, `-netdev user,id=isolated,restrict=on,hostfwd=tcp:127.0.0.1:19301-:19301,hostfwd=udp:127.0.0.1:19301-:19301`.
No Xray, no TPROXY, no physical router, no external network. Host uses IPv4 loopback exclusively and checks exact 25-byte payloads for separate TCP and UDP echo.

Job [124636789980](https://github.com/ment2/keenetic-vpn/actions/runs/41235004868/job/124636789980):
```
RC23_HOST: TCP_HOSTFWD_POSITIVE_CONTROL_25_BYTES 25
RC23_HOST: UDP_RETURN_TIMEOUT unconnected 1
RC23_HOST: UDP_RETURN_TIMEOUT unconnected 2
RC23_HOST: UDP_RETURN_TIMEOUT unconnected 3
RC23_HOST: UDP_RETURN_TIMEOUT connected 1
RC23_HOST: UDP_RETURN_TIMEOUT connected 2
RC23_HOST: UDP_RETURN_TIMEOUT connected 3
RC23_HOST: HARD_NO_GO_POSITIVE_UDP_RETURN_NOT_WITNESSED
RC23_GUEST: UDP_RX_EXACT seq=1 peer=10.0.2.2:60822 listener=19301 bytes=25
RC23_GUEST: UDP_SENDTO_EXACT seq=1 bytes=25
... (same for seq 2-3 and 4-6; separate host ephemeral ports 60822 and 35130)
```
Six byte-equal packets entered the guest, and six `sendto` calls reported 25 bytes. **No host UDP return was observed** by either unconnected or connected socket. Successful `sendto` is not wire-level delivery proof. The positive-control requirement fails closed and workflow is correctly FAILURE, not flaky SUCCESS.

QEMU's [official documentation](https://www.qemu.org/docs/master/system/invocation.html) says `restrict=on` isolates guest outbound but does **not** impact explicit forwarding rules. It is therefore unjustified to *attribute causality* to `restrict=on` alone. The precise unresolved component is MIPS guest UDP reply routing / PCnet / QEMU SLIRP hostfwd return path under this configuration. No authorized evidence of equivalent success has been obtained while keeping isolation.

## Exact original-destination outbound is also NOT proven

RC21's real ingress original destination was `10.0.2.15:19191`. It used `freedom.redirect=127.0.0.1:19292`, so the successful 25-byte backend receipts demonstrate only a *rewritten local destination*, not preserving the original destination for outbound. Earlier no-redirect topology used a guest backend bound to `0.0.0.0:19191` and Xray logged `fake: socket bind: address already in use` for UDP, which is a concrete same-namespace socket conflict. Removing redirect with the **same** backend topology is not a valid positive experiment.

New `xray/lab/rc23_original_destination_release_gate.py` requires: independent backend network stack, no freedom redirect or destination rewriting, raw real TCP/UDP original destination and outbound dial evidence, exact backend bytes, real host UDP return, hash-pinned MIPS Xray and guest kernel, post-death no-fallback and independent DNS/IPv6 no-leak. All-synthetic-true yields only `OFFLINE_REVIEW_CANDIDATE_ONLY`. The six regression tests (`tests/test_xray_v30_rc23_original_destination_gate.py`) explicitly reject RC21 synthetic redirect or missing UDP host return. These are **falsification contracts, not a packet-path substitute**.

To test true original destination safely next time, an independently isolated guest/backend network namespace/interface with packet delivery to a destination **not occupied by the TPROXY/Xray transparent reply socket** must be built and verified, including actual matching Xray dials and backend original destination. This has not yet been implemented or verified; do not claim otherwise.

## Privileged legacy / physical safety boundaries

RC22 tests reject seven legacy S97/S98/S99/watchdog/cron actor gaps, root cgroup-v1 escape, unknown or orphan descendants, stale PID/start-ticks/generation and untracked socket inodes. These remain **offline evidence gates only**. Observed privileged cgroup-v1 escape cannot be erased by synthetic fixtures. Physical KN-1810 vendor `4.9-ndm-5`, actual kernel modules, independent USB-less rescue, power-loss recovery, and original-five SHA restoration remain unverified.

**Release:** `RC23_HARD_NO_GO_POSITIVE_UDP_HOSTFWD_RETURN`; `RC23_ORIGINAL_DESTINATION_NOT_PROVEN`; `HARD_NO_GO_PRODUCTION`.

**Operations:** NO Keenetic jobs, production, main, snapshot, Cloudflare, physical firewall/routes/cron, merge, deploy, or live trial. No isolated-network restrictions relaxed.
