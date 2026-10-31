# RC22: direct-bypass negative probe, seven-actor lineage mutations, host UDP HARD NO-GO
**Date:** 2026-10-31. **Repository/branch:** ment2/keenetic-vpn / `feature/xray-v30-stable-tcp-ingress-lab-20261031`. **Mode:** immutable-hash disposable QEMU tests and offline-only verification. **Production:** HARD NO-GO.

## Verified real CI (no false-success substitutions)
- [RC21 MIPS Xray 26.2.6 TPROXY TCP/UDP to synthetic backend, 41233646934](https://github.com/ment2/keenetic-vpn/actions/runs/41233646934): SUCCESS, original ingress `10.0.2.15:19191` through `xt_TPROXY:12345`, `CAP_NET_RAW` Xray, redirected outbound backend `127.0.0.1:19292`, TCP and UDP each 25 bytes.
- [RC22 first attempt 41234280204](https://github.com/ment2/keenetic-vpn/actions/runs/41234280204): FAILURE because host harness watched stale RC21 readiness marker and sent **zero** baseline packets. Not a packet leak witness.
- [RC22 corrected 41234391436](https://github.com/ment2/keenetic-vpn/actions/runs/41234391436): **SUCCESS**, 6/6 RC22 static negative contracts, full-system Debian Malta MIPS32LE Linux `4.9.0-13-4kc-malta`, real Xray baseline and post-death packet challenge. Host `BASELINE_REAL_TCP_XRAY_ECHO 25`; guest `REAL_XRAY_TCP_UDP_BASELINE_BACKEND_PASS`; `XRAY_LISTENERS_GONE_AFTER_PARENT_OWNED_SIGNAL`; `POSTDEATH_SENTINEL_READY_SEND_PROBES`; `POSTDEATH_NO_SENTINEL_RECEIPT_BOUNDED_LAB_ONLY`. Guest required **increased both TCP and UDP `xt_TPROXY` counters after kill**. Host TCP probe timed out; host UDP return before/after remains unproven. Release markers explicitly `HARD_NO_GO`. Artifact [13054663824](https://github.com/ment2/keenetic-vpn/actions/runs/41234391436/artifacts/13054663824), SHA256 `2904630c3c7edf64788a4caa4261858889bb3cc2c8e8c16453c24901fc1daeb0`.
- [Offline CI 41234465887](https://github.com/ment2/keenetic-vpn/actions/runs/41234465887) **SUCCESS, 595/595** at `f5533a30bbe0f4acbdca4d1cb0d149c1a8bc8d95`. Six `test_xray_v30_rc22_privileged_lineage_gate.py` tests mutate each of seven exact legacy actor fences, boot/generation CAS, independent root kernel fence, unknown/root/out-of-scope/orphan PID1 child, PID/start-ticks reuse, socket-inode collision. No real router introspection or kernel enforcement occurs. `OFFLINE_REVIEW_CANDIDATE_ONLY` never authorizes production.

## Host UDP reply: unresolved independent infrastructure issue
RC19 original-port UDP echo already recorded guest receive of 25 bytes with host timeout in QEMU user/SLIRP `restrict=on` **without Xray**. RC21/RC22 equally lack host UDP return even though guest's backend receives original 25 bytes through Xray.
The [official QEMU invocation documentation](https://www.qemu.org/docs/master/system/invocation.html) explicitly states that `restrict=on` *does not affect explicitly configured host forwarding rules*. Therefore it would be unjustified to claim that the restriction itself explains the UDP reverse-path failure; need a separate controlled SLIRP UDP hostfwd baseline/return-path or an independently isolated host↔guest test without lifting restrictions. Host timeout is **not** a verified no-leak or end-to-end UDP PASS.

## Exact limitations of RC22 death probe
- The sentinel binds original guest destination *after* Xray exits. Under the tested kernel/mangle policy, the post-death ingress TCP+UDP counters increased while sentinel reported no exact matching payload. This establishes only **bounded non-receipt in this isolated fixture**.
- Parent-owned Xray direct-child PID/start-ticks is checked before lab-only TERM. This is not pidfd atomic signaling on Linux 4.9 and is **not** a race-free production watchdog replacement.
- Guest isolated SLIRP `-netdev user,restrict=on`; no external egress; no test of IPv6, DNS, multi-route fallback, or hardware reboot behavior.
- `freedom.redirect=127.0.0.1:19292` is **synthetic destination rewriting**. Preserving the independent original destination on outbound and bidirectional UDP return remains unproven.
- Offline seven-spawner evidence is a **falsification gate**, not a verified shutdown of actual production privileged S97/S98/S99/watchdog/cron descendants. Observed RC11 root escape from cgroup v1 independently prevents any containment claim.
- Actual Keenetic vendor kernel `4.9-ndm-5`, exact production SHA, USB-independent physical rescue/boot and power-loss-safe rollback are still untested.

## Release decision and prohibited changes
`RC22_DISPOSABLE_QEMU_POSTDEATH_NONRECEIPT_PASS`; `RC22_OFFLINE_595_TESTS_SUCCESS`; `HOST_UDP_RETURN_NOT_PROVEN`; **`HARD_NO_GO_PRODUCTION`**.

No Keenetic jobs, no main/snapshot/Cloudflare, production firewall/routes/cron, no merge/deploy or live trial. Next safe work item is separate disposable isolated return-path experiment that keeps `restrict=on`, with positive host UDP reply controls, and exact original-destination outbound proof; otherwise retain HARD NO-GO.
