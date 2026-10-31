# RC21 final run readback: MIPS32LE Linux 4.9 Xray UDP backend missing (HARD NO-GO)

**2026-10-31**, repository `ment2/keenetic-vpn`, only branch `feature/xray-v30-stable-tcp-ingress-lab-20261031`.
**Review-only GitHub Actions / offline evidence.** No Keenetic jobs, production, main, snapshot, Cloudflare, physical firewall/routes/cron, merge/deploy/live trial.

## Latest verified exact CI results

| Scope | Run | Conclusion | Caveat |
|---|---|---|---|
| RC11 native TPROXY after PIDFD change | [41229534586](https://github.com/ment2/keenetic-vpn/actions/runs/41229534586) | SUCCESS | Earlier commit fb24dc43 only |
| RC11 after /proc file-descriptor fix | [41229850515](https://github.com/ment2/keenetic-vpn/actions/runs/41229850515) | FAILURE | Five regression tests: `test_actual_pidfd_signal` false; not a global CI success |
| Later native TPROXY | [41230151110](https://github.com/ment2/keenetic-vpn/actions/runs/41230151110) | SUCCESS | Native Ubuntu kernel, not MIPS 4.9 |
| RC18 actual MIPS32LE userland dependency closure | [41231297244](https://github.com/ment2/keenetic-vpn/actions/runs/41231297244) | SUCCESS | Kernel module and MIPS executable checks |
| RC20 MIPS32LE 4.9 genuine xt_TPROXY packet ingress | [41232197650](https://github.com/ment2/keenetic-vpn/actions/runs/41232197650) | SUCCESS | Socket echo, **not Xray**, UDP host return not proven |
| RC21 Xray MIPS TCP+UDP | [41233103443](https://github.com/ment2/keenetic-vpn/actions/runs/41233103443) | **FAILURE** | Backend did not receive UDP before deadline |
| RC21 offline contracts | [41232776878](https://github.com/ment2/keenetic-vpn/actions/runs/41232776878) | SUCCESS | 578/578 synthetic/offline, NOT physical acceptance |

The exact RC21 job 124631187840 completed failure. Observed output:
```
RC21_HOST: REAL_TCP_TPROXY_TRANSPARENT_ECHO_RETURN 25
RC21_HOST: UDP_RETURN_NOT_PROVEN_SLIRP_RESTRICT_ON
RC21_GUEST: GUEST_RULES_FWMARK_TCP_UDP_INSTALLED
RC21_GUEST: Xray process witness pid=50 uid=65534 capeff=0000000000002000
RC21_GUEST: REAL_XRAY_UID65534_CAP_NET_RAW_NNP_AND_TPROXY_LISTENER_READY
RC19_GUEST: REAL_TCP_BYTES=25
RC21_GUEST: BACKEND_EXIT_OBSERVED=0
RC21_GUEST: HARD_NO_GO_UDP_BACKEND_NOT_RECEIVED_WITHIN_DEADLINE
RC18_GUEST: COMMAND_FAILURE MIPS_REAL_XRAY_TCP_UDP_TPROXY_INGRESS status=768
```
The Xray log excerpt displayed by the test only includes `RC9_CAP: BEFORE_EXEC...`; it is not evidence that UDP was processed by Xray. Exact missing witness: backend receipt of UDP **through real MIPS Xray**, plus host return and post-Xray-death fail closed.

## Verified boundaries and next strictly disposable investigations

- Real CI uses QEMU Malta MIPS32LE `4.9.0-13-4kc-malta` with checksum-verified MIPSel Xray 26.2.6, Debian Stretch libs and modules; **not** the vendor hardware kernel `4.9-ndm-5`.
- Guest `rc21_mips49_xray_packet.sh` routes TCP and UDP by TPROXY mark, starts real Xray and backend; it asserts true `CAP_NET_RAW` only. Missing UDP receipt is not cured by a longer artificial deadline or by assuming host SLIRP return.
- Additional non-production regression must independently record: UDP mangle PREROUTING counters before/after, Xray UDP listener `/proc/net/udp`, backend local recvfrom/bytes, Xray UDP routing log, exact original destination, and whether output loops back through TPROXY. Reject false positive where host sent UDP but guest backend did not receive it.
- Keep `-netdev user,restrict=on` or stronger isolation; do not allow unrestricted fallback to make CI pass. Limit changes to disposable paths, require SHA256 frozen artifacts, and record acceptance markers only on proof.
- Production HARD NO-GO regardless of future UDP test success: root/cgroup-v1 descendant escape, legacy S97/S98/S99/watchdog/cron not fully fenced, DNS/IPv6 no leak, and USB-independent physical boot rescue/power-loss remain unproven.

## Status

`RC21_MIPS_XRAY_UDP_BACKEND_HARD_NO_GO`, `PRODUCTION_HARD_NO_GO`.
This document does not modify scripts, routes, or real-device state and does not claim CI SUCCESS for RC21.
