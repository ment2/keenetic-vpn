# RC11 disposable PID identity patch and Linux4.9 MIPS netfilter feasibility (2026-10-31)

Scope only feature/xray-v30-stable-tcp-ingress-lab-20261031. No production/router jobs/network changes/deploy/merge.

## Implemented, not yet CI-certified
- New xray/lab/rc11_pidfd_guard.py: records PID start-ticks from /proc/PID/stat, uses pidfd_open before checking stat and command-line marker, rechecks start-ticks, signals exclusively via signal.pidfd_send_signal; no numeric kill fallback.
- Updated disposable xray/lab/rc10_native_tproxy_minimal_caps.sh: captures both child identities, uses pidfd guarded signal for cleanup and the deliberate Xray failure, skips ambiguous or unpinned targets (fail-closed). This is limited to synthetic runner namespaces, not S97/S98/S99/watchdog/cron.
- Added tests/test_xray_v30_rc11_pidfd.py: wrong start-ticks, wrong command marker, unpinned PID, exited PID, and actual pidfd signal of test-owned sleep process.
- Updated .github/workflows/xray-v30-rc10-native-cap-tproxy.yml to execute regression suite and shell syntax check, plus new file-trigger paths. Actual fresh workflow result is not yet verified. DO NOT report SUCCESS/517+ test count as an RC11 result without an Actions run.

## MIPS 4.9 TPROXY research
- Linux kernel 4.9 upstream supports CONFIG_NETFILTER_XT_TARGET_TPROXY (tristate); module is xt_TPROXY and target applies in mangle table. Related TPROXY support, iptables matches and policy routes are needed. This establishes *source-level feasibility*, not availability on vendor router.
- Public keenetic/kernel-49 repository is identified as MediaTek Linux 4.9 source. This alone does not prove an authorized, reproducible matching configuration, kernel image, initramfs, xt_TPROXY.ko, matching vermagic or bootable full-system MIPS32LE environment for specific KN-1810 firmware.
- Exact blocker for production-like MIPS packet path: no independently verified full-system MIPS32LE 4.9-ndm-5 kernel+rootfs+matching netfilter module artifacts and hashes in RC10 evidence. QEMU user-mode MIPS uses host kernel and cannot validate guest xt_TPROXY packet interception. Do NOT build or load unverified modules on router.
- Once independently pinned vendor-compatible artifacts exist, disposable full-system test must attest uname -m/-r, config flags, modinfo vermagic, successful module load, TCP/UDP packet counters, socket original destination, fwmark/rule/local route and fail-closed post-child-death for IPv4, then separate IPv6 and DNS no-leak.

## Release gate
RC11_PATCH_COMMITTED_UNVERIFIED_CI; HARD_NO_GO_PRODUCTION. Privileged cgroup-v1 escape, unmanaged legacy descendants, USB-independent physical boot and power-loss tests remain open. No new Keenetic jobs; no merge, deployment or live trial.

External research: https://cateee.net/lkddb/web-lkddb/NETFILTER_XT_TARGET_TPROXY.html ; https://cdn.kernel.org/doc/html/latest/networking/tproxy.html ; https://github.com/keenetic/kernel-49
