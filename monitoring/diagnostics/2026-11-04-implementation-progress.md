# VPN Monitoring: verified 2026-11-04 progress

## Read-only router discovery
- Keenetic ONLINE, Python 3.13.9. Xray PID 13546 uses `/opt/etc/xray/config.json`; legacy S98xray-wifi, xray-ks-home-watch, xray-watchdog run. No changes to these.
- Existing scripts present: xray_openai_probe.py, xray_server_check.py, xray-safe-hourly.sh; no sensitive config read.
- Python sqlite3, ssl, hashlib available; paho-mqtt absent.
- From Keenetic 192.168.0.135, Home Assistant 192.168.0.169 TCP connections to 8123 and 1883 succeed.
- MQTT v3.1.1 anonymous CONNECT returned CONNACK 20020005 (Not authorized). No message published. Broker reachable but requires authorization.

## Feature-branch implementation
- `monitoring/telemetry.py` provides stable non-credential node identity, strict allowlist schema, route-verification required for positive status, safe MQTT topic.
- `monitoring/tests/test_telemetry.py` has ten unit tests. Local offline copy: 10/10 OK.
- `.github/workflows/vpn-monitoring-tests.yml` added; GitHub CI result not yet confirmed.

## Integration dependency
To publish, create a dedicated least-privileged MQTT publisher identity for topic `keenetic/vpn-monitor/v1/#` using authenticated Home Assistant/Mosquitto administration. Do not disclose HA admin password or store secrets in code, library or GitHub.
An authenticated Home Assistant control channel is not connected to this chat. No HA changes were made.

## Safety
No production deployment or config modification, no restart, no pool switch, no firewall/routes/cron/watchdog modifications. RC36 hard NO-GO for seamless migration still holds.