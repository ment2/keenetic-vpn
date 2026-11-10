# RC45: IPv6 policy routing and IPv4 router-originated egress

Date: 2026-11-10. Branch: feature/xray-v30-stable-tcp-ingress-lab-20261031.

Existing read-only Keenetic job `da5099d2-1dde-436c-908a-e2a8ed54af28` returned done, exit_code=0, without resubmission.

## Confirmed
- IPv6 rules: priority 0 lookup local, priority 32766 lookup main; no other policy rules in output.
- IPv6 route table all contains `unreachable default dev lo` and `2001:2::c633:640b dev ezcfg0 ... linkdown`, ULA `fd78:f3d6:9214::/64 dev br0`, local/link-local entries. No usable global IPv6 default route in captured output.
- IPv4 `_NDM_BFD_OUTPUT` jumps to `Telnet_OUT`, `Http_OUT`, `Ftp_OUT`, `SSH_OUT`; `_NDM_IPSEC_OUTPUT_FILTER`, `_NDM_SSTPSRVVPN_OUT`, `_NDM_IKE1SRVVPN_OUT`, `_NDM_IKE2SRVVPN_OUT` empty in snapshot. Earlier IPv4 OUTPUT policy ACCEPT and `_NDM_ACL_OUT`, `_NDM_OUTPUT` empty. Not all nested BFD chains have been inspected.
- `ip route get 1.1.1.1` => `via 192.168.0.1 dev apclii0 src 192.168.0.135`. This establishes a non-VPN route selection for this router-originated destination, not proof that an actual packet leaked.
- Earlier FORWARD Home kill-switch uses XRAY_KS_HOME with duplicate rules; policy DROP; S98 flush/rebuild of XRAY_WIFI; watchdog can invoke S97 `killall xray`; TPROXY target currently not registered.

## Refined controlled-downtime no-leak and rollback gates
1. Identify scope explicitly: Home transit vs router-originated management/control traffic, Xray outbound-to-VPN endpoints, DNS, IPv6. Do not assume all router OUTPUT must traverse VPN: Xray's own transport requires a permitted underlay route.
2. Capture fresh boot ID, PID/start_ticks, routes and rules, kill-switch, backup hashes, supervisor identities and remote management reachability. Record expected egress for test destinations before maintenance.
3. Owner approved planned VPN downtime and session loss only. Any module, firewall, route, cron, or service writes require exact command and separate approval. Fence S98 destructive rebuild, watchdog->S97 restart, and competing writers while keeping independent kill-switch active.
4. Verify TPROXY module registration before two exact scoped TCP/UDP TPROXY rules. Avoid chain flush, blanket killall and modification of existing duplicate kill-switch rules.
5. Verify no-leak with independent witnesses: Home client traffic must not escape via underlay during VPN outage; explicitly allowed router control and Xray endpoint traffic distinguished from forbidden bypass; DNS and IPv6 checked; both TCP/UDP ingress and OpenAI health verified. Route lookup alone is not packet proof.
6. Roll back transaction-owned changes only, verify baseline, keep kill-switch enforced, recover Xray and re-enable supervisors after checking their logic; abort if management path or fail-closed cannot be proved. Same-USB backup/isolated restore verified, off-USB backup deferred.

Decision: HARD NO-GO for physical writes until separately approved and validated.
