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

## Follow-up completed: PREROUTING and inbounds
Job `c47de0e6-aa51-4fde-8452-3e0b1de885b5` completed exit 0:
- `PREROUTING` hook to `XRAY_WIFI`: **48 UDP packets / 30317 bytes**, **0 TCP packets**. The XRAY_WIFI chain had 0 TPROXY target hits in prior sampling, which is compatible with UDP being filtered by local/multicast RETURN rules; no proof of internet traffic interception.
- `FORWARD` first hook `XRAY_KS_HOME`: 40118 packets / 16075628 bytes cumulative.
- `br0` up, IPv4 `192.168.1.1/24`; nonsecret Xray inbounds: `local-socks` SOCKS `127.0.0.1:10808`, `tproxy-in` dokodemo-door `0.0.0.0:12345`.
- Conntrack text query for source `192.168.1.*` yielded 3 matching entries; insufficient to prove internet egress.
- Additional read-only snapshot queued: `0d4abb7b-f93f-4612-a3d8-de5d2a086c19` (chain detail, local client neighbor table, processes, IPv6 FORWARD, sanitized recent watchdog/error log). **Do not resubmit**.
**Conclusion:** Router-local SOCKS5 verified. Wi-Fi transparent interception remains **unverified**, and the active kill-switch has observed dropped packets. A real client-initiated request through Keenetic Wi-Fi is needed for end-to-end proof, after counters are sampled safely without resetting them.

## Continued polling of pending read-only diagnostic
Existing job `0d4abb7b-f93f-4612-a3d8-de5d2a086c19` remains `queued` after repeated polling. **No execution result exists yet**; no further claim is made about `ip6tables`, neighbor state or detailed TPROXY chain. No duplicate exec job was submitted.

`get_permission_status` still reports `remote_enabled=true`, `owner_admin_enabled=true`, revision 2, but this does not prove agent liveness. A separate `router_status` request returned diagnostic job `9ce78213-55c8-42a8-b6b2-ee21193dabdd` queued; it should be polled rather than repeated.

**Unresolved security exposure:** `br0` has a global-scope ULA IPv6 address (`fd78:...`), while observed kill-switch rules use IPv4 iptables. No conclusion about IPv6 leak protection can be drawn without read-only `ip6tables` and route checks. Avoid disabling IPv6 or firewall rules based on suspicion.

**Safe next:** await the existing read-only jobs, inspect exact `XRAY_WIFI` rule ordering and counters and IPv6 forwarding; then request a user-initiated Wi-Fi client test only if necessary to demonstrate end-to-end forwarding. No production changes made.

## Follow-up: TPROXY detail and IPv6 firewall — completed
Existing job `0d4abb7b-f93f-4612-a3d8-de5d2a086c19` completed, exit 0; agent diagnostic `9ce78213-55c8-42a8-b6b2-ee21193dabdd` completed exit 0 (Keenetic ONLINE, Python 3.13.9, load 0.79/0.52/0.5, 3.53 GB free).

- `XRAY_WIFI` has **two PREROUTING references**. Packet counters: 27 RETURN packets for `192.168.0.0/16` and 37 RETURN packets for `224.0.0.0/4`. Both TCP and UDP TPROXY targets have **0 packets**. Thus traffic reaching the chain in this sample was excluded; no external TCP/UDP traffic intercepted.
- Xray process PID 13546; `S98xray-wifi`, `xray-ks-home-watch.sh`, and `xray-watchdog.sh` processes running.
- ARP/neighbor entries show one `STALE` IPv4 neighbor `192.168.1.81` and several `FAILED` neighbors. `FAILED` alone does not prove a Wi-Fi outage or a specific client's status.
- IPv6 `FORWARD` policy is **DROP** and includes router-native `_NDM_*` chains plus `RELATED,ESTABLISHED` ACCEPT, but no explicit `XRAY_KS_HOME` or TPROXY IPv6 rule in the displayed FORWARD chain. This is **not proof** of IPv6 leak or fail-closed behavior; require complete ruleset, IPv6 default route and counters.
- Watchdog log documents SOCKS5 unavailability and automatic Xray recovery at **2026-10-30 06:52** and **07:50 MSK**. The log does not demonstrate present outage, but raises a reliability concern; no restart triggered by this audit.

Read-only job `492fd1a7-409e-4497-af1a-a6ca71259ce1` queued to check IPv6 default route, FORWARD counters, mangle rules, kill-switch rules and upstream addresses. Do not resubmit. Full Wi-Fi end-to-end proof still requires a client to generate actual external traffic through Keenetic.

## IPv6 follow-up resolved as current non-routing, not proven leak
Read-only job `492fd1a7-409e-4497-af1a-a6ca71259ce1` completed exit 0:
- `ip -6 route show default` returned **no IPv6 default route**.
- `br0` has ULA `fd78:f3d6:9214:0:52ff:20ff:fe46:775d/64` and link-local `fe80::...`. A global-looking `2001:2::c633:640b/128` exists only on **DOWN / NO-CARRIER** interface `ezcfg0`; this does not establish usable WAN IPv6.
- `ip6tables FORWARD` policy **DROP**, every displayed forwarding counter **0**, no Xray IPv6 TPROXY rules; IPv6 mangle PREROUTING contains only `_NDM_*` native chains. Therefore **no evidence of current IPv6 internet egress or leak**, but also **no tested IPv6-over-VPN support**. Future WAN IPv6 activation must trigger a new leak test; avoid a blanket claim of permanent leak protection.
- IPv4 Xray Wi-Fi PREROUTING hooks exist for TCP and UDP from `192.168.1.0/24`, `br0`; `XRAY_KS_HOME` returns for `192.168.0.0/16` and DROPs remaining `br0` traffic from `192.168.1.0/24`. IPv4 default route via `192.168.0.1` on `apclii0`.
- Still **0 TCP and UDP TPROXY-target hits** at the last sampling. This cannot prove that a live client has made an external request.

### Test gate: real client action required
To verify transparent routing without changing production, connect a phone to **Keenetic LAN/Wi-Fi network 192.168.1.0/24** (not the upstream 192.168.0.0/24 network), disable cellular data for the test, open a normal HTTPS page (e.g. `https://ifconfig.me/ip`) and report whether it opens and which **public IP** it shows. Do not send credentials or private IPs. Follow up by sampling existing counters and public egress. No automatic route/iptables/kill-switch changes are authorized by this test.
