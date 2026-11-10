# RC45: FORWARD / OUTPUT / IPv6 / policy routing read-only evidence

Date: 2026-11-10. Branch: feature/xray-v30-stable-tcp-ingress-lab-20261031.

Existing task `a14afaa2-66c0-4b93-a331-efac7e5c7cc8` completed `done`, `exit_code=0`, no resubmission.

## Verified rules
- IPv4 FORWARD policy DROP; two identical `-A FORWARD -j XRAY_KS_HOME` jumps at head.
- `XRAY_KS_HOME`: six duplicate `-d 192.168.0.0/16 -j RETURN`; seven duplicate `-s 192.168.1.0/24 -i br0 -j DROP`.
- IPv4 OUTPUT policy ACCEPT with NDM subchain jumps. No direct proof of router-originated leak or no-leak.
- IPv6 OUTPUT policy ACCEPT with NDM subchain jumps. IPv6 FORWARD, interfaces and routes not yet inspected.
- Policy route priority 20000 `fwmark 0x40000000/0x40000000 lookup 100`; table 100 `local default dev lo scope host`. Other policy rules include priority 10, priority 1164 for 192.168.0.135, and default local/main/default rules.

## Updated controlled-outage migration gates
Owner permits planned VPN outage and loss of active sessions, **not** unreviewed writes. Prefer sequential stop/start over seamless dual-Xray handoff. Snapshot boot ID, PID/start_ticks, chain, routes, backup SHA, independent kill-switch and recovery access. Preserve kill-switch and management reachability; fence S98 destructive XRAY_WIFI rebuild and watchdog S97 restart (`killall xray`) plus cron writer races. Existing duplicates are a separate issue: do not remove or flush them as part of the two-rule change. Require separate exact-command approval for module activation and for precisely two scoped TCP/UDP TPROXY rules. Validate TCP/UDP, DNS, IPv6, router-originated OUTPUT, no-leak/fail-closed, and rollback. Same-USB backup/extraction verified; off-USB recovery deferred.

**HARD NO-GO** for production writes. Read-only next step: inspect IPv4/IPv6 OUTPUT subordinate chains and IPv6 FORWARD/addresses/routes, without secrets.