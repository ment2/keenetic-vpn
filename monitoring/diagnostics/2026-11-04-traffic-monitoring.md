# Interface traffic telemetry (2026-11-04)

Status: isolated development + read-only router canary. NOT installed.

## Actual Keenetic evidence
Task 22b69ce3-cf75-4209-bd2d-d80cabf00aab done exit 0: /sys/class/net/<iface>/statistics/rx_bytes and tx_bytes readable. Counters observed:
- apclii0 RX 50,559,415,931 B; TX 8,164,980,751 B
- br0 RX 1,747,196,738 B; TX 10,571,383,393 B
- br1 RX 3,390,851,658 B; TX 23,803,613,638 B
These are cumulative and NOT exclusively VPN. Traffic on virtual and bridge interfaces can overlap, so never sum them as total usage.
Xray production config: api_present=false, stats_present=false, policy_stats=false; 8 outbounds and 2 inbounds. Thus accurate per-VLESS-server bytes are not currently observable through built-in Xray Stats API without a separately tested configuration change.

Task 485c503a-6147-4b15-b03b-584ead061305 done exit 0: bounded 3.003 s sample on apclii0: RX +1,467 B; TX +745 B; RX rate 0.00391 Mbps; TX rate 0.00198 Mbps. Proof of concept only.

## Development
- monitoring/traffic_counters.py: read-only interface snapshots and reboot-aware deltas; rejects negative counters, discontinuities and overly long gaps.
- monitoring/tests/test_traffic_counters.py: 10 tests; locally tested equivalent logic 10/10 PASS. GitHub Actions status unconfirmed.
- Proposed sampling every 60 seconds, store UTC and monotonic timestamps, boot ID, interface, raw counters, deltas and rates. First sample is baseline. Weekly/monthly totals from valid intervals only, reset/gap flagged.
- Monitor apclii0, br0 and br1 independently, prevent double counting and distinguish WAN/bridge from VPN-specific metrics.
- MQTT/Home Assistant publication pending dedicated auth. Broker reachable at 192.168.0.169:1883 but anonymous CONNECT rejected (code 5).

No changes to Xray, routes, firewall, cron, watchdog or Home Assistant. No scheduled monitoring deployed.