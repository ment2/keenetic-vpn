# RC31 seven legacy root descendant fencing and MIPS49 dual-Xray first TPROXY cutover evidence

Date 2026-10-31. Repository ment2/keenetic-vpn, only branch feature/xray-v30-stable-tcp-ingress-lab-20261031. This document distinguishes **first cutover** from RC30 postdeath SUCCESS.

## Verified negative packet evidence
[First TPROXY cutover run 41238827244](https://github.com/ment2/keenetic-vpn/actions/runs/41238827244) **FAILURE**, at SHA 33e8bdea. Real disposable MIPS Linux4.9 QEMU host received exact 19-byte TCP and UDP echo from the independent original-destination backend before cutover, and exact replies for old and new TCP/UDP flows during cutover. However the guest refused to proceed because its four-rule owner witness could not prove all intended TPROXY owners; `RC30_GUEST_HARD_NO_GO_BOTH_TPROXY_OWNERS_NOT_WITNESSED`, preventing the rollback-ready stage. The host raised `RC30_HARD_NO_GO_STAGE_MISSING RC30_GUEST_CUTOVER_RULES_REMOVED_ROLLBACK_READY`. Hence **NO VERIFIED SEAMLESS TPROXY CUTOVER OR ROLLBACK**.

[Run 41238983743](https://github.com/ment2/keenetic-vpn/actions/runs/41238983743) again **FAILURE** at stage and owner counter witness, even though all six original/new TCP+UDP host echo requests succeeded. These bytes alone cannot prove per-process ownership. An independent offline CI [41238942146](https://github.com/ment2/keenetic-vpn/actions/runs/41238942146) failed on cron shared-generation test; a literal comment about flock is not executable fencing. The new independent RC31 gate (offline only) is added to require seven source SHA256 snapshots and fail closed on missing, drifted, PID-reused, privileged, orphan or unproven physical fencing. It is NOT proof that any process is actually fenced.

## Independent verified baseline
[RC29 41238192710](https://github.com/ment2/keenetic-vpn/actions/runs/41238192710) **SUCCESS** real original destination TCP+UDP (22 bytes). [RC30 postdeath 41238549653](https://github.com/ment2/keenetic-vpn/actions/runs/41238549653) **SUCCESS** bounded no-direct postdeath TCP/UDP canary, with live backend. These **do not** prove *first dual-Xray TPROXY cutover*.

## Hard release blockers
- Seven privileged legacy entrypoints: S97xray (killall), S98xray-wifi, S99xray-watchdog, xray-watchdog.sh, xray-wifi-rules.sh, xray-fc-cron-guard.sh, xray-safe-hourly.sh. Offline source SHA fingerprints are **not live hashes**.
- Actual RC11 privileged root process escaped cgroup v1, kernel fencing unproven; physical kernel KN-1810 `4.9-ndm-5` not tested.
- PID/start-ticks/boot ID and generation CAS lack physically enforced original actor/descendant authority, socket inode exclusion and durable atomic journal. Missing exact UDP tuple ownership remains release blocker.
- Independent USB-less cold-boot rescue, original-five SHA restoration and power-loss rollback not verified on real hardware.

**HARD_NO_GO_PRODUCTION** regardless of any offline green. Never send Keenetic jobs or touch production, main, snapshot, Cloudflare, real firewall/routes/cron, merge, deploy, live trial.

## Verified corrected first cutover and RC31 CI

- [Dual-Xray RC30 known tuple CI 41239188032](https://github.com/ment2/keenetic-vpn/actions/runs/41239188032) **SUCCESS** at `6341bee7be381cd3c5ad56ef8039f2b700653b53`, all steps green, 7 targeted tests. Real host exact TCP+UDP old before/during/after rollback and new during/after rollback. Independent original-dest backend received echoes and guest emitted `RC30_GUEST_CUTOVER_RULES_REMOVED_ROLLBACK_READY` and `RC30_GUEST_TWO_XRAY_PID_STARTTICKS_UNCHANGED_GENERATION_CAS_SYNTHETIC`.
- [Dual-Xray RC30 known tuple CI 41239200367](https://github.com/ment2/keenetic-vpn/actions/runs/41239200367) **SUCCESS** again at `65a491e26a53ff1a5912890b523a7776065f4b1d`, all steps green, 8 targeted tests, real TCP/UDP exact payload and rollback witnesses independently repeated. The legitimate proof is **only** one pre-registered TCP source port 21111 and UDP source port 21112 retained on legacy, and test-controlled new ports through API-enabled candidate. No universal flow-pin test, production firewall rule acceptance, durable CAS, or root-watchdog fence.
- [RC31 offline seven-actor CI 41239253164](https://github.com/ment2/keenetic-vpn/actions/runs/41239253164) **SUCCESS** at `9daad1fa8c4dd32b08a9486071f8474c1adebf45`, all steps green, **7/7 tests**, emitted `RC31: SEVEN_VERSIONED_LEGACY_SHA256_SNAPSHOTS_ONLY_HARD_NO_GO`.
- [Full offline source regressions 41239253080](https://github.com/ment2/keenetic-vpn/actions/runs/41239253080) **SUCCESS**, **673/673 tests**, same RC31 source commit.

The old [41238827244](https://github.com/ment2/keenetic-vpn/actions/runs/41238827244) remains **FAILURE** for its own source commit. It must never be retroactively called SUCCESS just because later fixed commits passed. During that failed run old/new UDP and TCP echo bytes reached the backend, but owner counter gate prevented rollback. The later successful runs prove a narrower, specifically pre-registered known-tuple cutover.

**Deployment:** still `HARD_NO_GO_PRODUCTION`. The seven files in RC31 are *versioned repository snapshots*, not live router readbacks. Real privileged root cgroup-v1 escape (RC11), root watchdog/cron descendant fencing, universal UDP five-tuple ownership, filesystem journal generation CAS, independent physical USB-less rescue, actual NDM vendor kernel and DNS/IPv6 no-leak remain **unverified**. No router jobs, main/snapshot/Cloudflare, production routes/firewall/cron, merge/deploy or live trial were performed.

