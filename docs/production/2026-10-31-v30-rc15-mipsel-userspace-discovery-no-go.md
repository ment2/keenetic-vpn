# RC15 MIPS32LE packet-path userland dependency discovery, review-only

Date: 2026-10-31. Restricted branch: `feature/xray-v30-stable-tcp-ingress-lab-20261031`. Based on RC13 in-guest successful kernel module load and RC14 dual-provenance reconciliation.

Scope: SHA256/ELF discovery of official archived Debian Stretch mipsel `iptables 1.6.0`, `iproute2 4.9.0`, and `busybox-static 1.22.0` package bytes on isolated GitHub runner. The discovery workflow **does not execute MIPS binaries**, load any kernel modules, create namespace or alter any route; no packet-path claims. Exact SHA256 must be extracted from successful runner evidence and **pinned in source before execution**.

Remaining packet-path gate: validated complete dynamic loader and extension library closure; boot a disposable QEMU MIPS32LE Linux 4.9 kernel with NIC/veth topology, load same-ABI `xt_TPROXY`/netfilter modules, apply guest-only iptables mangle TPROXY and fwmark/table routing; send **real TCP and UDP payloads** from external namespace/guest to a real Xray transparent inbound and backend; assert payload equality, iptables counters, listener UID/caps/PID/start-ticks, crash no-fallback, plus DNS/IPv6 no-leak. RC13 `-net none` was module-only.

Privileged legacy S97/S98/S99/watchdog/cron cgroup-v1 root escape is **experimentally confirmed**. Offline synthetic fencing CAS, orphan and no-leak contract checks are not equivalent to live hardware proof. USB-independent boot/rescue, vendor `4.9-ndm-5` and actual physical power interruption remain separate HARD NO-GO gates.

**Release decision HARD_NO_GO_PRODUCTION.** No router jobs, no production/main/snapshot/Cloudflare/firewall/routes/cron/merge/deploy/live trial.
