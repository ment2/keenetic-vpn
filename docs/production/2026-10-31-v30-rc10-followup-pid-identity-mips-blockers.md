# RC10 follow-up: independently inspected blockers and test-hardening requirements (2026-10-31)

Scope: ment2/keenetic-vpn, branch feature/xray-v30-stable-tcp-ingress-lab-20261031 only. Read-only source audit and documentation; no router job, no production, main, snapshot, Cloudflare, firewall, routes, cron, merge, deploy or live trial. This document does NOT assert RC11 CI success.

## Verified inputs
- RC10 source blob: xray/lab/rc10_native_tproxy_minimal_caps.sh = 9b5b0f6c14b59d37eaa0fd17c27890e6a8895660.
- RC10 release manifest blob: xray/staging/v30-rc10-linux49-capability-tproxy-cas-rescue-review.json = 1752f38a0680cf2e56f4cb5d5a8ecdddbd06c191.
- Prior CI 41225001745 has completed source-contracts job marked success. Previous independently recorded Linux4.9 guest CI 41224765496 and native packet test 41224152158 were not rerun in this audit.

## Specific new issue: RC10 native TPROXY teardown process identity
In rc10_native_tproxy_minimal_caps.sh, cleanup() decides whether to signal xray_pid by checking /proc/$pid/cmdline against qemu-mipsel or /xray, and whether to signal server_pid by checking a substring. These checks do NOT require matching the original /proc/$pid/stat start-ticks at the instant before signaling. Mainline assertions record START_TICKS only after the process starts, but cleanup does not use it. PID reuse with a matching command line could therefore signal an unrelated runner process; initial empty/start-failure branches have the same vulnerability. No evidence of an actual PID reuse incident. Required fix: capture identity promptly for both children, compare pinned PID+start-ticks before each signal, use pidfd when supported by disposable host or fail closed on mismatch/unreadable state; avoid broad cmdline-only authorization and never signal an ambiguous PID. Race-free signaling may require pidfd_send_signal; /proc read+kill alone does not eliminate the final race.

## RC10 infrastructure blocker, not a production approval
The manifest explicitly states Debian x86_64 4.9 guest, while packet-path proof runs on a newer Ubuntu x86_64 host kernel. Thus no successful combined MIPS32LE + 4.9-ndm-5 + real TCP/UDP TPROXY path is evidenced. No vendor MIPS 4.9-ndm-5 bootable kernel/rootfs/netfilter modules have been verified from immutable, authorized inputs. Do not claim MIPS full-system packet proof based on qemu-mipsel user-mode (host kernel), or based on cross-architecture 4.9 x86_64 VM. Need pinned MIPS32LE 4.9-compatible kernel and matching xt_TPROXY/netfilter modules, configuration and module vermagic; test actual IPv4 TCP and UDP packets, capabilities, routing mark and fail-closed behavior entirely inside disposable full-system guest. If unavailable, record exact missing artifacts and HARD NO-GO instead of fabricating success.

## Privileged legacy descendants and boot constraints
Observed privileged cgroup v1 migration escape in RC10 remains a counterexample to cgroup-only fencing. Review-only acceptance requires immutable inventory of S97/S98/S99/watchdog/cron descendants and write/kill permissions, owned process trees, exact generation CAS, PID/start-ticks and fail-closed when owner ambiguous. Physical USB-independent boot guardian, independent storage durability and genuine power-loss remain unproven; QEMU two-boot ext4 scenarios are not equivalent. Prohibit live cutover until these are verified via separately approved hardware acceptance.

## Release decision
DISPOSABLE_RC10_EVIDENCE_ONLY; HARD_NO_GO_PRODUCTION. New document is audit evidence only. No new runtime CI was triggered, no changed executable source, no new verified test count. Next authorized task: implement strictly disposable process-identity teardown hardening with regression tests, then run CI and record actual IDs and results. Continue kernel/module availability research only through disposable, properly pinned sources.
