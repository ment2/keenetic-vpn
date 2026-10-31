# RC13: real MIPS32LE Linux 4.9 Netfilter module load, packet-path HARD NO-GO

**Date:** 2026-10-31. **Only branch:** `feature/xray-v30-stable-tcp-ingress-lab-20261031`. **Initial RC11:** `92d1357b`. **No production authority.**

## Verified executable evidence

[RC13 QEMU full-system CI 41229379759](https://github.com/ment2/keenetic-vpn/actions/runs/41229379759) **SUCCESS**. This is real guest Linux `4.9.0-13-4kc-malta` on QEMU `system-mipsel -M malta -cpu 4KEc`, not Linux host user-mode. The runner checked the archived package SHA256 `9a5dff9c498bf5736ca9f97cbb005b4b60bd139aa0f30f5bab9feca783907d9b` and vmlinux SHA256 `20f5380e02f2e40d4495fd61a854e5867f5ccdf95c8c1fd3d53fe27e8be1797f`.

Host `modinfo` established this dependency order: `x_tables, ip_tables, iptable_mangle, nf_defrag_ipv6, nf_defrag_ipv4, xt_socket, xt_TPROXY`. Guest `SYS_init_module` succeeded for **all 7 actual MIPS32LE .ko**, and in-guest `/proc/modules` confirmed all five principal components, with explicit `REAL_MIPS49_NETFILTER_XTABLES_TPROXY_MODULES_LOADED` marker.

[RC12 discovery CI 41229212015](https://github.com/ment2/keenetic-vpn/actions/runs/41229212015) **SUCCESS** pinned the native MIPS module architecture and same-kernel vermagic of `xt_TPROXY`, `xt_socket`, `iptable_mangle`, `ip_tables`, and `x_tables`. [RC12 offline CI 41229212028](https://github.com/ment2/keenetic-vpn/actions/runs/41229212028) **SUCCESS, 559/559 tests** including legacy fencing/rescue/no-leak refusals.

## Limits and next exact blocker

The RC13 guest used `-net none`. It **did not** execute TCP/UDP packet delivery via `xt_TPROXY`, did not start a MIPS userland `iptables`/policy routing tool or configure a NIC, `fwmark`, `ip rule`, local table 100, Xray backend, packet generator or DNS/IPv6/no-leak probes. Modules load proof is not end-to-end packet-path proof.

A later **disposable-only** experiment could pin and verify exact Debian MIPS32LE `iptables_1.6.0+snapshot20161117-6_mipsel.deb`, `iproute2_4.9.0-1+deb9u1_mipsel.deb`, their matching runtime libs and isolated guest NIC topology, then demonstrate actual TCP+UDP payload bytes/counters, no fallback after parent-owned Xray crash, IPv6/DNS leak isolation and complete rollback. These candidate packages were identified from Debian's public archive; no SHA256/exec verification yet.

Root privileged descendant cgroup v1 escape **already reproduced in real MIPS kernel 4.9 RC11**. Cooperative `flock` or two `/proc` scans alone cannot fence legacy S97/S98/S99/watchdog/cron root spawners. No physically proven USB-independent boot guardian, separate power domain, interrupted rollback on vendor `4.9-ndm-5`, live Xray SHA/PID/start-ticks, or no-leak certification. RC12 offline gate remains fail-closed.

**Production: HARD_NO_GO_PRODUCTION** despite successful module inventory and load. Nothing touched router, production, main, snapshot, Cloudflare, existing firewall/routes/cron. No Keenetic jobs, merge, deploy or live trial.

## CI hygiene

First RC13 offline run **41229379727** found one false-positive static assertion that matched the phrase "no iptables mutation" in a comment, not an executed action. Source is unmodified. The source test was narrowed in commit `f7c8d813`; a follow-up offline CI result must be reviewed independently before treating the revised suite as green.
