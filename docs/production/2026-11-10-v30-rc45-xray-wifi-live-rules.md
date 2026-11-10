# RC45: verified live XRAY_WIFI rules and boot identity

Date: 2026-11-10. Repository ment2/keenetic-vpn, branch feature/xray-v30-stable-tcp-ingress-lab-20261031.

Existing Keenetic read-only job `65ac984c-e99d-4b25-a74c-00f95b151788` returned `done`, `exit_code=0`; no resubmission.

- Kernel: `4.9-ndm-5`.
- Boot ID: `17cc872c-36cb-4411-899e-9eec5f3155c9`.
- Direct `iptables -t mangle -S XRAY_WIFI` output: chain exists and has exactly nine RETURN rules, in order, for `0.0.0.0/8`, `10.0.0.0/8`, `100.64.0.0/10`, `127.0.0.0/8`, `169.254.0.0/16`, `172.16.0.0/12`, `192.168.0.0/16`, `224.0.0.0/4`, `240.0.0.0/4`.
- Zero TCP and zero UDP TPROXY rules in chain.
- TPROXY not listed in `/proc/net/ip_tables_targets`; `xt_TPROXY` not listed in `/proc/modules`.
- Previous quick parser output `RETURN 8 TPROXY 0 APPEND 0` was unreliable and superseded by the full direct listing.

Decision: **HARD NO-GO** for live module activation, two-rule TPROXY change or API cutover. Kernel target activation, competing S98/S97/watchdog/cron writer fencing, independent rollback and fail-closed acceptance remain unproven. USB archive integrity and isolated extraction were verified, but backup and restore-test remain on same USB. Owner deferred off-USB backup. Do not publish VPN config, archive or secrets.

Any new Keenetic write requires a separate owner approval of the exact command.