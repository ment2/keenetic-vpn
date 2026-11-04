# VPN Monitoring: MQTT account and TLS gate (2026-11-04)

User confirmed creating dedicated non-admin local-only Home Assistant account `keenetic_monitor`; password is not supplied to assistant and must not be stored in GitHub or Library.

Verified Keenetic router diagnostics:
- MQTT TCP 1883 reached Home Assistant 192.168.0.169; previous anonymous MQTT 3.1.1 CONNECT yielded CONNACK 0x05 (Not Authorized).
- New read-only TLS connection attempt on 192.168.0.169:8883 yielded ConnectionRefusedError (errno 146). Port field shown in Mosquitto app does NOT establish listener availability.
- No broker, Xray, firewall, route, cron, watchdog or HA settings modified.
- `monitoring/mqtt_local_auth_check.py` implements an interactive localhost/container-network-only, no-PUBLISH credential check, password hidden. `monitoring/tests/test_mqtt_local_auth_check.py` has offline protocol-framing tests. CI status unconfirmed.

Next: identify whether `python3` or `mosquitto_pub` exists in Advanced SSH & Web Terminal add-on. Validate username/password only locally with non-echoing input, never paste secret into ChatGPT. For persistent router→HA MQTT, provision TLS with validated certificate and least-privilege topic access or an alternative encrypted channel after separate review. Never send credentials via unencrypted 1883 over Wi-Fi.
