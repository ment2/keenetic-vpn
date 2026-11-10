# RC45 — Controlled-downtime Xray v30 change request

Date 2026-11-10. **DRAFT / HARD NO-GO for live writes.**

## Approved operational scope
Owner permits planned VPN downtime, loss of TCP/UDP sessions, direct WAN for Home clients during maintenance and temporary direct WAN during rollback. This does **not** authorize Keenetic writes, module loads, firewall, routes, service signals, cron or config changes.

## Verified RC45 baseline
Kernel 4.9-ndm-5; boot ID 17cc872c-36cb-4411-899e-9eec5f3155c9. TPROXY module files exist but target is not registered. XRAY_WIFI has nine RETURN exclusions, zero TPROXY. Mark 0x40000000/0x40000000 routes to table 100, local default dev lo. S98 PID file 757; 60s loop invokes xray-wifi-rules.sh which flushes/rebuilds XRAY_WIFI. Watchdog 30s checks SOCKS5 10808 and invokes S97 restart; S97 stop uses killall xray. Kill-switch watcher 15s reasserts XRAY_KS_HOME and FORWARD jump. XRAY_KS_HOME contains six duplicate RETURN and seven duplicate DROP rules, plus two duplicate FORWARD jumps. Cron every 15m stages config.pending.json without restart under flock; separate OpenAI monitoring cron. IPv4 OUTPUT ACCEPT; route to 1.1.1.1 via 192.168.0.1 dev apclii0 src 192.168.0.135. IPv6 main default unreachable; IPv6 OUTPUT ACCEPT, FORWARD DROP. Same-USB backup verified for checksum and isolated extraction, off-USB recovery deferred.

## Ordered change with independent gates
A. **Read-only preflight**: recheck boot ID, PID/start_ticks, process descendants, S97/S98/S99/cron ownership, full firewall/routing baseline, backup SHA, candidate config, independent management and underlay exceptions. Abort on drift, missing candidate, unavailable backup or recovery access.
B. **Separately approved maintenance fencing**: bounded, generation/boot-ID-checked fencing of S98 chain rebuild, watchdog->S97 killall, cron and any respawners. Verify descendants and no respawn; no blanket killall. Keep management access. Exact commands blocked pending verified control ownership.
C. **Separately approved direct-WAN mode**: Home br0/192.168.1.0/24 may use WAN during maintenance. XRAY_KS_HOME currently blocks it, and watcher reasserts chain. Require narrow, reversible, independently validated exception; do not blindly delete duplicates or flush chains. If safe exception is unproven, leave clients offline and request separate decision.
D. **Separately approved TPROXY and sequential Xray cutover**: stop old Xray after watchdog fencing; accept session loss. Activate kernel target only after explicit module-load approval and verify registration. Append precisely two TPROXY rules after nine RETURN exclusions, conditional on chain identity:
```sh
/opt/sbin/iptables -t mangle -A XRAY_WIFI -p tcp -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000
/opt/sbin/iptables -t mangle -A XRAY_WIFI -p udp -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000
```
These are **proposed only**, not authorized. Apply validated v30 config via atomic/rollback-capable procedure; start and test SOCKS5, TPROXY TCP/UDP, DNS, IPv4/IPv6, OpenAI and real packet paths.
E. **Production acceptance**: verify designated VPN traffic goes through Xray, underlay/server connections use allowed WAN; restore normal kill-switch and VPN routing before ending window. Resume supervisors only if their logic cannot destroy new state. Record witnesses and hashes.
R. **Rollback**: remove only transaction-owned rules, restore previous verified config and service state, check boot/generation and chain identity; direct WAN allowed during rollback. Restore normal policy before closing maintenance, otherwise report degraded fallback. No blind full-tar extraction.
Proposed exact inverse, **not authorized**, only when transaction owns unique matches:
```sh
/opt/sbin/iptables -t mangle -D XRAY_WIFI -p udp -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000
/opt/sbin/iptables -t mangle -D XRAY_WIFI -p tcp -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000
```

## Approval requirements
Before any physical write, present exact literal commands, expected outputs, abort criteria and independent rollback for supervisor fencing, temporary Home WAN exception/inverse, Xray stop/start, module load, two rule additions/removals, config swap/restore and validation. Owner must explicitly approve them. **HARD NO-GO remains** until remaining read-only ownership/insert-point gates are resolved.