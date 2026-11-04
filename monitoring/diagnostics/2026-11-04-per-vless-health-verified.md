# Per-VLESS monitoring: verified development state, 2026-11-04

Repository `ment2/keenetic-vpn`, branch `feature/vpn-monitoring-home-assistant-20261104`.

## Real router verification

- Original production Xray stays running on PID 13546; no restart or configuration changes.
- Traffic monitoring had 14 completed `CYCLE_OK` and 0 `CYCLE_FAILED` in read-only verification.
- Built 7 stable hashed IDs via `monitoring/vpn_inventory.py`, with no VLESS UUIDs, public keys, domain names or config secrets printed.
- Existing standalone probe `/opt/bin/xray_server_check.py` audited: creates temporary configuration and a separate Xray process, terminates only its child in `finally`. It was executed once on `vpn01`, then as a bounded full-pool batch. Each of seven VLESS routes returned `status=ok` with actual external IP and country code. This does not tell which outbound served regular users or its bytes transferred.
- Initial exit witnesses: vpn01=DE (78.17.178.91), vpn02=NL (140.225.199.92), vpn04=DE (78.17.178.113), vpn05=DE (78.17.178.113), vpn06=RU (178.72.144.171), vpn07=RU (95.129.234.51), vpn09=US (152.53.242.98).
- `/opt/tmp/vpn-monitoring-lab/monitoring/vpn_node_probe.py` verified single route `vpn02`, returned node ID `node_5b5540efcce46d0683d2`, route_verified=true, test_duration_ms=2414. The duration is a full end-to-end test, **not RTT**.
- `/opt/tmp/vpn-monitoring-lab/monitoring/vpn_health_discovery.py` generates 28 HA MQTT sensor discovery configurations, 4 for each node, intended retained. Not yet published.
- `/opt/tmp/vpn-monitoring-lab/monitoring/vpn_health_collector_loop.py` runs one isolated Xray test at a time, designed for 900-second cadence, separate lock and JSONL history, optional QoS1 MQTT using a router-local secret. Not yet started.
- Combined offline test suite on real Keenetic: **54/54 OK** (job `c9ca287c-6370-44c3-88a6-90dfc3d4071c`).

## Important limits

- Main Xray config currently has `observatory` with 60s interval and `leastPing` balancer, but its Stats API/policy aren't enabled. No actual per-outbound byte counts or user-session routing attribution is available from current collected information.
- The interface metrics from `apclii0`, `br0`, `br1` cannot be aggregated as unique VPN traffic or attributed to VLESS tags.
- Health probes consume small real network traffic and test outbound functionality; do not equate successful probe with continuous availability.
- MQTT credential file was never read through assistant remote connector; user has confirmed local authentication and QoS1 publication.
- Automatic startup across router reboot has NOT been enabled. No production Xray, firewall, routes, cron, S97/S98/S99 or watchdog changes.

## Local-only next activation

Use Termius locally to publish the 28 HA MQTT discovery configurations and start a detached 15-minute health collector. It will print a PID; status must be confirmed using `ps`/the separate log and via Home Assistant device entities. Do not modify the running traffic sampler.

For rollback, terminate only the exact PID whose command line contains `monitoring.vpn_health_collector_loop`; never `killall`, and do not delete retained discovery blindly. No need to restart Xray or the router.
