# VPN Monitoring: MQTT auth confirmed and one-shot collector staged

Date: 2026-11-04.

Owner manually ran the prior local MQTT protocol test on Keenetic and reported `MQTT_AUTH_OK`. This proves the broker accepted the dedicated `keenetic_monitor` login from the local Termius test, but it does **not** establish that MQTT publishing and subscriber delivery have succeeded.

## Development in feature branch
- `monitoring/traffic_one_shot.py`: read-only snapshot of `apclii0`, `br0`, and `br1`; stores previous counters in a local restricted state directory; detects baseline/deltas/reset/gaps via `traffic_counters.py`.
- Optional `--publish` flag sends non-retained, JSON QoS1 data to `keenetic/vpn-monitor/v1/traffic/<iface>`, using existing `mqtt_lan_publisher.py`. Script accesses the router-local password only when invoked locally.
- `monitoring/tests/test_traffic_one_shot.py`: 5 local offline tests passed, including no secret access without explicit publishing, and topic construction.
- `monitoring/mqtt_lan_publisher.py` already prepared; developer tested simulation only. No GitHub Actions CI completion verified.

## Safety and limitations
- No remote reading of secret files: tool guard blocked such action earlier, do not repeat or reroute.
- No router installation, MQTT test publish, hourly service/cron, Xray change, main merge, HA dashboard or runtime collector was performed.
- Interface bytes are **not per-VLESS traffic**; bridge and wireless counters overlap. Avoid double-counting.
- The first measurement is a baseline, not a valid traffic delta. For byte-per-minute, capture 2 samples. Reboot and unexpected decreases are distinct from genuine bytes.
- Follow-up required: a user-run on-router local canary, because it needs the local password. After MQTT PUBACK, move to approved bounded scheduling and optional Home Assistant MQTT sensors.
