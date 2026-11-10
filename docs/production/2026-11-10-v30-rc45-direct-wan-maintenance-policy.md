# RC45: planned downtime with explicitly permitted direct WAN

Date: 2026-11-10. Repo: ment2/keenetic-vpn. Branch: feature/xray-v30-stable-tcp-ingress-lab-20261031.

## Owner-approved operational policy
During a separately approved planned VPN maintenance window, client traffic may use direct WAN and existing VPN sessions may break. During rollback, temporary direct WAN is also acceptable. This is an acceptance-policy change, **not** permission to edit router firewall, services, routes, cron or modules. Outside the approved maintenance window, restore the agreed production VPN routing policy and validate it.

## Existing read-only job evidence
Keenetic task `3b545b76-eb49-4a4c-b218-868adcf23629` returned done, exit_code=0, without resubmission.

- `Telnet_OUT`: TCP source port 23 DROP with `_NDM_BFD_Telnet4` ipset match.
- `Http_OUT`: TCP source ports 80,443 DROP with `_NDM_BFD_Http4`.
- `Ftp_OUT`: TCP source ports 20,21 DROP with `_NDM_BFD_Ftp4`.
- `SSH_OUT`: TCP source port 22 DROP with `_NDM_BFD_SSH4`.
- These BFD rules do not establish a blanket router OUTPUT kill switch.
- `ip route get 1.1.1.1` -> `via 192.168.0.1 dev apclii0 src 192.168.0.135`. Route selection alone does not prove packet leakage.
- `XRAY_KS_HOME` has 13 rules, consistent with six duplicated RETURN and seven duplicated DROP rules observed earlier; FORWARD also had two duplicate jumps.
- Boot ID unchanged: `17cc872c-36cb-4411-899e-9eec5f3155c9`.

## Revised fencing and rollback acceptance
1. Read-only preflight: boot ID, PID/start-ticks and descendants, S97/S98/S99/watchdog/cron identities, Xray/config SHA, module registration, TPROXY chain/routing baseline, independent management access and same-USB backup verification.
2. Agree explicit maintenance start/end and direct-WAN scope. S98 60-second XRAY_WIFI flush/rebuild and watchdog 30-second S97 `killall xray` must be fenced for the maintenance transaction, along with conflicting writers. Keep unrelated services and remote management reachable.
3. If direct WAN is required for Home clients, the existing `XRAY_KS_HOME` FORWARD DROP will require a separately approved, narrow, reversible adjustment. Do not assume owner policy automatically changes firewall. Avoid blanket flush, permanent kill-switch removal, or deletion of pre-existing duplicates.
4. With separate exact-command approval, stop legacy Xray sequentially; activate and verify TPROXY target if needed; add precisely scoped TCP/UDP TPROXY rules; apply candidate configuration and restart Xray. Session continuity is not required.
5. During maintenance/rollback, direct WAN is permitted and is not a no-leak failure. Check management availability, DNS, TCP/UDP and IPv6 for intended routing and absence of unintended isolation; log the maintenance window. Verify VPN-specific egress and OpenAI reachability after successful cutover.
6. Roll back only transaction-owned firewall/routes/config changes; restore supervisor and kill-switch state according to the explicitly approved final mode; verify baseline identities, routing and client connectivity. Do not blindly restore the whole tar archive. Off-USB backup remains deferred.

## Decision
Read-only findings confirmed. Physical module/firewall/service/route/cron changes remain **HARD NO-GO pending separate exact-command authorization**. No live changes were performed.