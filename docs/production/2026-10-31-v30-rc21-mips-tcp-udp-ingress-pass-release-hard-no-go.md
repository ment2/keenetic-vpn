# RC21 follow-up: confirmed MIPS32LE Xray TCP+UDP transparent ingress, synthetic localhost backend, production HARD NO-GO

**Date:** 2026-10-31. **Repository:** `ment2/keenetic-vpn`. **Only branch:** `feature/xray-v30-stable-tcp-ingress-lab-20261031`.
**Scope:** disposable QEMU MIPS32LE Debian Linux 4.9 `4.9.0-13-4kc-malta` with SHA256-pinned official Xray 26.2.6. Not Keenetic device, vendor `4.9-ndm-5`, hardware acceptance, or deployment permission.

## Root cause: initial RC21 UDP backend failure, now isolated

In [failure 41233279539](https://github.com/ment2/keenetic-vpn/actions/runs/41233279539) actual guest mangle TPROXY PREROUTING counters were **TCP 6 packets / 269 bytes; UDP 3 packets / 159 bytes**. Xray logged per UDP datagram original destination `10.0.2.15:19191` followed by `app/proxyman/inbound: connection ends > fake: socket bind: address already in use`. The test backend simultaneously bound `0.0.0.0:19191`; the test setup made its backend port collide with the original TPROXY destination and Xray's transparent UDP reply socket. Therefore the UDP bytes reached kernel/Xray but not the backend. Evidence supports a test topology bind collision, **not** an intrinsic MIPS `xt_TPROXY` failure.

## Strictly disposable corrective change

- The host-facing original destination stays `10.0.2.15:19191`; guest `iptables -t mangle PREROUTING` preserves real TCP and UDP TPROXY `--on-port 12345`, `fwmark 0x40000000`, policy routing table 100.
- Only inside disposable guest QEMU, the synthetic backend now binds a separate port **19292**. The guest-only Freedom outbound uses `settings.redirect=127.0.0.1:19292`. This explicitly **rewrites outbound destination for the lab**, so it is **not proof of production original-destination preservation through direct Freedom**.
- `-netdev user,id=isolated,restrict=on` stays unchanged. Host port forwards stay bound exclusively to `127.0.0.1:19191`. No external default route, no unrestricted guest networking or device access is added.
- Guest asserts real TCP listener and both UDP ports 12345 / 19292 in `/proc/net/udp` or `/proc/net/udp6`, with bounded readiness. It rejects the previously seen `fake: socket bind: address already in use`, missing real backend byte receipt, and missing positive TPROXY counters.
- The shared RC19 echo source retains original default port 19191; RC21 compiles **only its copy** with `-DPORT=19292`. Historical RC19 UDP host SLIRP-return timeout remains an unrelated unproven requirement.

## Direct CI evidence and outcomes

| Run | Exact status | Meaning |
|---|---|---|
| [41233536253](https://github.com/ment2/keenetic-vpn/actions/runs/41233536253), `e4378545` | **SUCCESS** | First real MIPS Xray TCP and UDP 25-byte backend receipts after separate synthetic port |
| [41233551239](https://github.com/ment2/keenetic-vpn/actions/runs/41233551239), `ddb4d97c` | **FAILURE** | New socket assertion read IPv4 UDP before Xray readiness/without IPv6 alternative; fail closed, no false PASS |
| [41233589851](https://github.com/ment2/keenetic-vpn/actions/runs/41233589851), `a403987e` | **FAILURE** | Five static contracts PASS; strict UDP socket readiness still too early |
| [41233646934](https://github.com/ment2/keenetic-vpn/actions/runs/41233646934), `68ca1bac` | **SUCCESS** | Five / five static isolated topology/packet release contracts plus real QEMU MIPS TCP+UDP ingress backend; bounded v4/v6 UDP socket readiness |
| [41233576278](https://github.com/ment2/keenetic-vpn/actions/runs/41233576278), `18b2a33d` | **SUCCESS** | Existing separate offline source contracts, does not certify physical release |

The successful [run 41233646934](https://github.com/ment2/keenetic-vpn/actions/runs/41233646934), job `124632789772`, produced:
```
Ran 5 tests in 0.000s
OK
RC13_GUEST: REAL_MIPS49_NETFILTER_XTABLES_TPROXY_MODULES_LOADED
RC21_GUEST: UDP_XRAY_LISTENER_12345_AND_BACKEND_19292_CONFIRMED
RC21_GUEST: REAL_XRAY_UID65534_CAP_NET_RAW_NNP_AND_TPROXY_LISTENER_READY
RC19_GUEST: REAL_TCP_BYTES=25
RC19_GUEST: REAL_UDP_BYTES=25
RC19_GUEST: REAL_TCP_UDP_ECHO_BYTES_PASS
RC21_GUEST: REAL_XRAY_BACKEND_TCP_UDP_AND_TPROXY_COUNTERS_GUEST_LOOPBACK_REDIRECT_ONLY
RC21: PASS_REAL_MIPS49_XRAY_TCP_UDP_TPROXY_INGRESS_BACKEND_ONLY
RC21_HOST: UDP_RETURN_NOT_PROVEN_SLIRP_RESTRICT_ON
RC21: HARD_NO_GO_UDP_RETURN_DIRECT_FALLBACK_PHYSICAL_USB_RESCUE
```
Artifacts: [RC21 serial and logs](https://github.com/ment2/keenetic-vpn/actions/runs/41233646934/artifacts/13054497004). Actual package and binary SHA256 are pinned and verified by RC21 runner before execution.

## Remaining HARD NO-GO gates, unchanged

1. **Bidirectional UDP to host:** UDP host return is not confirmed under QEMU SLIRP `restrict=on`, although guest backend received payload. Do not weaken isolation to manufacture a pass.
2. **True original-destination preservation:** guest-only outbound redirect intentionally rewrites destination for the test. No direct Freedom UDP path to an independent external backend with unmodified original destination has been proven.
3. **MIPS hardware:** QEMU Debian Malta MIPS32LE Linux 4.9 is NOT Keenetic KN-1810 vendor `4.9-ndm-5` kernel/hardware; on-device `xt_TPROXY`, capabilities, firewall policy and actual device configuration remain unverified.
4. **No-leak / fail closed:** no full MIPS IPv6/DNS UDP/TCP no-leak and Xray-death fallback denial witness, including physical reboot.
5. **Privileged legacy fencing:** S97/S98/S99, watchdog, cron and descendants not universally fenced; observed privileged cgroup v1 escape is a counterexample.
6. **Physical independent rescue:** separate USB-independent boot path, hardware power-loss fsync/recovery, original-five byte-exact rescue and owner-approved SHA acceptance not proven.

**Disposition:** `RC21_DISPOSABLE_MIPS_XRAY_TCP_UDP_INGRESS_BACKEND_PASS`; `HARD_NO_GO_PRODUCTION`. No new router jobs, no bypass, production/main/snapshot/Cloudflare/firewall/routes/cron edits, merge/deploy/live trial.
