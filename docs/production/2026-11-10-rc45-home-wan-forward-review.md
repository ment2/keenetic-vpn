# RC45: Home direct WAN, FORWARD and NAT review

Date: 2026-11-10. Repo `ment2/keenetic-vpn`, branch `feature/xray-v30-stable-tcp-ingress-lab-20261031`.

## Evidence

Existing read-only task `8886b0b6-e3ed-4566-a0bb-81d2412a1a0d` returned `done`, exit 0, without resubmission.

- `_NDM_HOTSPOT_FWD` has `-i br0 -j RETURN`, plus other exemptions; this is not an ACCEPT.
- `_NDM_UPNP_FORWARD_SYS` and SSTP/IKE1/IKE2 forwarding chains empty.
- `_NDM_SL_PROTECT` jumps to `_NDM_SL_PRIVATE`, then `-i br1 -m state --state NEW -j ACCEPT`; no corresponding explicit `br0` ACCEPT in the shown chain.
- `_NDM_MASQ_BYPASS` exempts multicast source/destination `224.0.0.0/4` only. `_NDM_MASQ` has Home `192.168.1.0/24` MASQUERADE for non-br0 output, conditional on ndmmark.
- `ip route get 1.1.1.1 from 192.168.1.10 iif br0` selects `via 192.168.0.1 dev apclii0`. This is a route lookup, not proof of packet acceptance or NAT.
- FORWARD policy DROP, two jumps to XRAY_KS_HOME; kill-switch chain has six pre-existing destination RETURN duplicates and seven Home DROP duplicates. Owner permits direct WAN during maintenance and temporary rollback, not live modifications.

## Revised direct WAN / fencing / rollback plan

1. Before a physical operation, read `_NDM_SL_PRIVATE`, inspect counters and check actual packet path without changing rules; ensure remote management remains independent of VPN.
2. Fence S98 rebuild, watchdog->S97 restart, kill-switch watcher and cron updater using fresh boot ID/PID/start_ticks and descendant checks; avoid S97 blanket `killall xray` until verified safe. S99 and Telegram children require separate awareness.
3. A simple `RETURN` in XRAY_KS_HOME is **insufficient** to authorize Home direct WAN because the FORWARD policy is DROP. An early ACCEPT in XRAY_KS_HOME is **not approved** because it bypasses system security chains. Do not add an extra NAT rule until mark/path acceptance is confirmed.
4. Proposed TPROXY TCP/UDP rules and conditional inverses remain in the prior RC45 change request; activation of kernel modules, config switch and service operations require exact separately approved commands.
5. Roll back only transaction-owned rules/config/process changes. Temporary direct WAN during rollback is allowed; before closing maintenance verify final routing, VPN health, DNS, TCP/UDP, IPv6 and management access. Same-USB backup verified; off-USB deferred.

Pending read-only task `1e7c0ee4-9287-49b3-b178-b02a4ad2e927` checks `_NDM_SL_PRIVATE`, counters and boot ID. Poll only; do not resubmit.

**HARD NO-GO** for router writes. No physical changes performed.
