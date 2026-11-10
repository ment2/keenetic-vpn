# RC45: IPv4/IPv6 OUTPUT, IPv6 FORWARD, routes and no-leak gates

Date: 2026-11-10. Branch: feature/xray-v30-stable-tcp-ingress-lab-20261031.

Existing read-only Keenetic job `46aabc7a-7a01-4b86-8761-848a0f5c0c0b` completed `done`, `exit_code=0`; not resubmitted.

## Verified observations
- IPv4 `_NDM_ACL_OUT` and `_NDM_OUTPUT` chains exist and are empty.
- IPv6 `_NDM_ACL_OUT` and `_NDM_OUTPUT` chains exist and are empty.
- IPv6 FORWARD policy `DROP`, with system ICMPv6, state, ACL, VPN, delegated and forwarding chains; this is not a full IPv6 kill switch proof.
- No IPv6 default route in the displayed main-table `ip -6 route show` snapshot. Host route `2001:2::c633:640b` via `ezcfg0` is linkdown.
- `br0` has ULA IPv6 `fd78:f3d6:9214:0:52ff:20ff:fe46:775d/64`; `ezcfg0` has `2001:2::c633:640b/128` (global scope but interface down).
- Earlier: IPv4 and IPv6 OUTPUT policy `ACCEPT`; IPv4 FORWARD policy `DROP`; duplicate kill-switch RETURN/DROP and FORWARD jumps; TPROXY target not registered and XRAY_WIFI contains nine RETURN rules but zero TPROXY.

## Interpretation
No main-table IPv6 default route reduces apparent IPv6 egress exposure in this snapshot, but does not prove absence of policy routes, other tables or future RA changes. Empty two OUTPUT subchains do not prove other NDM chains are empty. Router-originated IPv4 fail-closed is not proven. No measured leak is claimed.

## Controlled-outage plan (not executed)
1. Read-only preflight: fresh boot ID, PID/start_ticks/descendants, management path, firewall/routing baseline, verified same-USB backup, kill-switch, IPv6 policy routes and DNS ownership.
2. Separate exact-command approval for time-bounded fencing of S98 destructive rebuild, watchdog->S97 `killall xray` and cron races. Preserve independent kill-switch and remote access. Planned VPN outage and active-session loss are permitted, not unreviewed writes.
3. Separately approve module activation and verify registered TPROXY target before any firewall writes.
4. Separately approve exactly two scoped TCP/UDP TPROXY rules after nine RETURN exclusions, with exact-match rollback and no global flush. Do not touch existing duplicate kill-switch rules in this change.
5. Sequential stop, validated candidate apply, restart and test SOCKS5, TPROXY TCP/UDP, DNS, IPv6, router OUTPUT, OpenAI and no-leak/fail-closed.
6. Roll back transaction-owned changes only, verify baseline and independent kill-switch, re-enable supervisors after verifying they cannot overwrite state. No blind full-tar restore.

**HARD NO-GO** for physical writes until separate authorization, proven fencing/rollback and no-leak gates.