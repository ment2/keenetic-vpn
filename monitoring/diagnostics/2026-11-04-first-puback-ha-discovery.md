# 2026-11-04: First MQTT publish and HA discovery development

## Confirmed by owner
- Owner executed local Termius one-shot publish using the existing `keenetic_monitor` account and local password file.
- Output was `MQTT_PUBLISH_OK`; the command required successful CONNACK and MQTT QoS1 PUBACK packet `40020001` before printing. This confirms acceptance by the Mosquitto broker, not delivery to Home Assistant's MQTT integration or creation of an HA sensor.
- One-shot published non-retained interface counter data on `keenetic/vpn-monitor/v1/traffic/apclii0`. No claim of scheduled telemetry or HA history.

## New implementation
- `monitoring/homeassistant_discovery.py` generates Home Assistant MQTT discovery topics for 12 entities: 4 per monitored interface `apclii0`, `br0`, `br1` (RX total, TX total, RX bit/s, TX bit/s).
- `monitoring/mqtt_lan_publisher.py` supports retained discovery payloads with MQTT QoS1 and a restricted discovery topic prefix, while ordinary telemetry remains non-retained.
- `monitoring/tests/test_homeassistant_discovery.py` tests topic naming, expiry, device grouping, interface allowlist and retained discovery.
- GitHub CI completion not yet verified. Home Assistant MQTT integration/discovery enabled state also not verified.

## Design decisions
- HA discovery configs retained to survive Home Assistant MQTT reconnect; measurement messages NOT retained, and sensors expire after 240s when missing updates. See HA official MQTT documentation.
- Counters from Linux interfaces are not per VLESS server; do not add across wireless and bridge layers as if independent.
- Reboots/reset/gaps must be handled in the collector; first sample is only a baseline.
- MQTT credentials are local in root-only router file. Never call remote tools to read it: prior call was blocked by safety controls.

## Current release gates
- No discovery topics sent to broker; no verified HA sensors; no automatic scheduling, broker changes, router production changes, cron/services/watchdog changes, or merge/deploy.
- Before enabling automation: test local collector on router, verify HA MQTT integration exists and discovery is enabled, verify bounded CPU/I/O, ensure rollback and explicit consent for service installation.
