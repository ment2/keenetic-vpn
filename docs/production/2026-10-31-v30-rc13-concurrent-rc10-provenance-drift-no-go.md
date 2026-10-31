# RC13 follow-up: immutable RC10 source-pin drift blocks current aggregate CI

**Date:** 2026-10-31. **Branch only:** `feature/xray-v30-stable-tcp-ingress-lab-20261031`. Production **HARD NO-GO**.

## Proven and independently green

- MIPS Linux4.9 module inventory: [RC12 CI 41229212015](https://github.com/ment2/keenetic-vpn/actions/runs/41229212015) SUCCESS. Matching SHA-pinned MIPS32LE `xt_TPROXY`, `xt_socket`, `iptable_mangle`, `ip_tables`, `x_tables` kernel modules.
- Real MIPS guest loading: [RC13 CI 41229379759](https://github.com/ment2/keenetic-vpn/actions/runs/41229379759) SUCCESS. Seven in-kernel `init_module` calls and `/proc/modules` verification. Guest `-net none`, **NOT** packet flow.
- Offline source contracts with the corrected RC13 static test: [CI 41229505578](https://github.com/ment2/keenetic-vpn/actions/runs/41229505578) SUCCESS **563/563** on commit `f7c8d813`.
- Existing x86_64 native disposable TCP/UDP TPROXY ran successfully again in CI 41229534586, but it is **not MIPS Linux4.9**.

## Separate concurrent source drift detected

Another parallel feature-branch contribution changed `xray/lab/rc10_native_tproxy_minimal_caps.sh` to use stronger PID/start-ticks/pidfd cleanup. This changed the Git blob from the original pinned `9b5b0f6c14b59d37eaa0fd17c27890e6a8895660` to `9164b2cf57010c53a7cf90b2421940ac1b00aa60` in the observed CI. The immutable RC10 manifest still requires the older value, so subsequent aggregate run [41229534611](https://github.com/ment2/keenetic-vpn/actions/runs/41229534611) is **FAILURE** on `test_seven_exact_git_blob_hashes`, despite newer native TPROXY CI passing. The current feature-branch aggregate suite **cannot** be represented as green.

**Required reconciliation:** preserve historical RC10 evidence, treat the modified disposable source as a new version, independently review the PID/start-ticks/pidfd change, version a separate source pin/provenance and rerun offline + native + full-system CI together. Do not rewrite old RC10 provenance silently; no force/revert of another contributor's work without explicit review.

## Remaining release gates

MIPS Linux4.9 exact **TCP/UDP packet path with NIC + iptables TPROXY + fwmark + local route + real Xray and no-leak** still unproven. Actual MIPS cgroup v1 **root legacy descendant escape** remains established. No live complete S97/S98/S99/watchdog/cron fencing, no independent physical power/USB boot/rescue, no vendor NDM5 no-leak attestation.

**HARD_NO_GO_PRODUCTION.** GitHub documentation and Library report only. No router jobs, production/main/snapshot/Cloudflare/firewall/routes/cron/merge/deploy/live trial.
