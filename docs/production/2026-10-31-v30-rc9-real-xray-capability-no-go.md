# Keenetic Xray v30 RC9: real Xray capabilities and fail-closed rescue

**Date:** 2026-10-31. **Scope:** feature branch only, no changes to router or production.

## Verified CI

- Full-system QEMU CI [41222202057](https://github.com/ment2/keenetic-vpn/actions/runs/41222202057): **SUCCESS**. Real official Xray **26.2.6 linux/amd64** inside Linux **6.8.0-147-generic**, two scenarios and four full guest boots.
- Offline contract CI [41222515983](https://github.com/ment2/keenetic-vpn/actions/runs/41222515983): **SUCCESS, 508/508 tests**. Exact source Git SHA pins and production prohibition.
- Guest logs artifact **13050721397**, retained until 2026-11-14. All four boot logs were downloaded and inspected.

Official SHA256 checks are enforced before guest boot:

| Archive or file | SHA256 |
| --- | --- |
| Xray-linux-64.zip v26.2.6 | `29ce535b56e207a406ffa1c2d4842dcc410be003eff8ec508bb732abc9f8e385` |
| xray linux/amd64 executable | `3f650abf1fc4a4fbf5abe7fc9990a2658020907cd984214e9c075b4b00989fea` |

## Real guest TCP/UDP permissions

The guest sets UID/GID 65534 and `no_new_privs` **before exec**. The no-capability profile failed to enable `IP_TRANSPARENT` on both TCP and UDP sockets. A profile with **only `CAP_NET_RAW`**, effective capability mask `0x2000`, passed both socket operations. Under this restricted profile the genuine Xray binary opened a real TCP+UDP transparent-mode inbound. Its process `CapEff` and `NoNewPrivs` were verified directly.

This establishes the socket API and listener privilege requirements for the tested x86_64 guest kernel. It **does not** prove packet redirection through the MIPS router's TPROXY rules, IPv6/DNS no-leak, or physical Linux 4.9 support. Linux ambient capabilities exist in upstream Linux since 4.3, but vendor kernel feature and permissions still require confirmation.

## Parent-owned crash and guardian identity

A fresh direct parent created a genuine Xray child. It recorded PID and `/proc` start ticks durably before an induced parent failure. The separate guest observer verified that the child's network listener disappeared and the recorded identity was not replaced. No signal was sent to a PID obtained from the historical receipt. All four guest boots passed.

This is **direct parent supervision**, not the full multi-guardian generation-CAS protocol. The earlier MIPS32LE 8+8 guardian experiment remains separately verified in CI [41215515431](https://github.com/ment2/keenetic-vpn/actions/runs/41215515431).

## Rescue unavailable: second boot fails closed

First boot: private virtual ext4 rescue/active disks plus simulated USB, original five script SHA256 checks, journal synced after 2/5 replacements, abrupt VM shutdown.

Second boot: a **blank substitute rescue disk**, simulated USB absent. Guest refused to restore because `SHA256SUMS` was missing. The runner compared all five active files **before and after** the second guest boot: **zero additional writes**. The baseline with its verified rescue disk restored 5/5 successfully.

All storage devices were disposable virtual images on a single GitHub runner. This is **not** an actual independent rescue device or a physical power-loss test.

## Versioned sources and controls

The feature branch includes the six RC9 components: `rc9_guest_capwrap.c`, `rc9_guest_socket_cap_probe.c`, `rc9_guest_parent_crash.c`, `rc9_fullvm_init`, `rc9_fullvm_runner.sh`, and `xray-v30-rc9-fullsystem.yml`. Exact source Git blob SHA values and all release-denial conditions are pinned by `xray/staging/v30-rc9-real-xray-capability-review.json`, with automated contract tests.

## Physical Linux 4.9 acceptance: HARD NO-GO

The archived Keenetic read-only evidence reported `4.9-ndm-5`, lacking pidfd support. No full-system **Linux 4.9** kernel was exercised in RC9; QEMU used **6.8 x86_64**, and the production Xray is MIPS32LE. No new router jobs were submitted.

Before considering any physical pilot, permitted read-only evidence must establish actual kernel config and capabilities, cgroup-v1 and complete legacy S97/S98/S99/watchdog/cron descendant fencing, current Xray binary/permissions, complete IPv4+IPv6 TCP/UDP TPROXY/DNS/kill-switch safety, and an independent physically verified USB-free boot guardian. A separate owner-approved exact-file rollback plan is mandatory.

**Release decision: HARD_NO_GO_PRODUCTION.** No router production/Cloudflare/firewall/routes/cron/main/snapshot modifications, merge, deploy, or live trial.
