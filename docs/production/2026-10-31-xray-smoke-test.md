# Production Xray VPN functional smoke test — 2026-10-31 00:07–00:09 MSK

**Environment:** Keenetic Ultra KN-1810, Xray 26.2.6 linux/mipsle, running config `/opt/etc/xray/config.json`. Read-only diagnostics, no deployment, restart, firewall/cron/route edit, or live config disclosure.

## Verified PASS
- Keenetic agent online, Python 3.13.9, load average 0.39/0.44/0.52, free disk 3.53 GB (diagnostic job `0578eb71-ee87-4c06-a067-c770bdf0191c`).
- Xray process running PID **13546** and SOCKS5 listener `127.0.0.1:10808`.
- HTTPS through SOCKS5 to `https://www.google.com/generate_204`: HTTP **204** in **0.416 s**.
- Direct HTTPS comparison: HTTP **204** in **0.417 s**. This comparison does not establish public VPN egress IP.
- OpenAI API through SOCKS5: `https://api.openai.com/v1/models` returns **HTTP 401** in **0.872 s** without authentication, demonstrating successful network/TLS/API reachability; 401 is expected for missing credentials.
- Both active and staged `config.pending.json` pass `/opt/sbin/xray run -test -config ...`: **Configuration OK**.
- TPROXY port **12345** listening, `XRAY_WIFI` mangle chain contains TCP/UDP TPROXY rules, PREROUTING hooks exist for `192.168.1.0/24`, fwmark `0x40000000` routes to table 100, local default route to loopback present.
- Kill-switch `XRAY_KS_HOME` exists and is hooked into FORWARD, with DROP for `br0` `192.168.1.0/24` after local-network RETURN.
- Watchdog and kill-switch watch processes running, cron daemon running.
- Update log at 00:01:22: `PENDING_UNCHANGED`, verified candidate staged but **NOT applied**. Active config SHA256 `66d074f32fffbf4a251576c8297714e9647174546e9e73e5bf27cf2768efe6d7`; pending SHA256 `79dc423b52e5f5c4d3cc88c34487756d8c229f2705e7670b1e2c839966e289b8`.

## WARN / not yet established
- Telegram IP probes `149.154.167.50/.51/.91` via HTTPS returned TLS errors; these are **not** conclusive Telegram failures, since Telegram MTProto on TCP/443 is not necessarily HTTPS. Separate SOCKS5 TCP-connect-only test queued under job `bf641e41-f467-4227-b2df-bcaa3b7efa86`.
- Xray warns that gRPC transport, VLESS without Flow, and legacy Host header use deprecated features. Configuration is currently accepted; migration should be planned and tested separately.
- Xray version initially probed using wrong `/opt/bin/xray` path (not found); corrected to `/opt/sbin/xray` and version verified.
- Full Telegram application end-to-end success, DNS leak resistance, IPv6 handling, actual Wi-Fi client egress IP, kill-switch outage simulation, automated failover and recovery **not** established by these non-disruptive checks.
- **Do not run live kill-switch outage tests or restart Xray without a separate maintenance plan and rollback.**

## Reproducibility and source
Snapshot branch `snapshot/keenetic-production-2026-10-30` contains 63/63 source files matching live SHA256 and Git executable bits. The snapshot is not the installed Xray binary or a full router clone. Diagnostic job IDs `7680afb4-ccc4-49a9-b9a0-140c4946e740` and `73b70b97-5818-49dd-ba90-50c0ae553a02` completed with exit code 0.

**Status:** Core Xray and SOCKS5 functional smoke tests PASS; comprehensive VPN integration tests remain partial. Production unchanged.

## Follow-up: traffic counter warning
Read-only job `bf641e41-f467-4227-b2df-bcaa3b7efa86` completed:
- Telegram TCP-only probe **not executed** because the router's curl was built without `telnet://` support. Previous HTTPS-to-IP errors cannot establish Telegram availability.
- `XRAY_WIFI` TPROXY TCP and UDP counters were **both 0 packets** at sampling time.
- `XRAY_KS_HOME` DROP counter was **956 packets / 382524 bytes**, local RETURN counter 2 packets / 123 bytes. Counters are cumulative, so this is evidence of dropped LAN transit traffic but not its current rate.
- Agent Python process was running.
**Important:** This means **Wi-Fi client VPN forwarding is not yet verified and may be broken**, despite working SOCKS5 and present firewall rules. Do not report whole VPN as healthy. Further read-only check of PREROUTING/FORWARD counters and actual Xray inbound is queued as job `c47de0e6-aa51-4fde-8452-3e0b1de885b5`. Do not reset counters, disable kill-switch or alter production without a separate change plan.
