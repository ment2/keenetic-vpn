# Keenetic VPN Monitoring + Home Assistant

Status: PLANNING; not deployed. Date: 2026-11-04.

## Purpose
Create passive/read-only long-term monitoring of individual Xray/VLESS VPN servers, quality, outages, egress IP and configuration generation; publish trends to Home Assistant on existing mini-PC. This is a separate feature branch of ment2/keenetic-vpn.

## Verified prior context
- Keenetic Ultra KN-1810, Entware, Xray, existing individual OpenAI test using isolated temporary Xray/SOCKS. Expected HTTP 401 from unauthenticated OpenAI API means reachable, not API authorization.
- Existing vpnNN tags can change identity on subscription reordering; telemetry requires stable, privacy-preserving node ID.
- RC36 disposable CI passes do not lift HARD NO-GO for silent UDP session migration or privileged legacy S97/S98/S99/watchdog fencing. Monitoring must not implement automatic cutover.
- User screenshots: Home Assistant OS 18.4, Core 2026.10.4, Supervisor 2026.10.5, Frontend 20260930.5. Host homeassistant, IP 192.168.0.169/24, gateway 192.168.0.1, Wi-Fi ASUS-Mnt2 (wlan0), interface end0 also shown, HA UI 8123.
- Mini-PC reachability from Keenetic, SSH, add-on availability, MQTT and network segmentation are not yet confirmed.

## Proposed telemetry
Per node: timestamp, stable node_id, ephemeral vpnNN alias, endpoint host/IP and port (redacted as appropriate), transport, selected route witness, external egress IP, geo/ASN, OpenAI/Telegram/other endpoint HTTP-TLS-TCP success, RTT, timeout/error type, packet loss when valid, Xray binary/config hash or generation, probe schema version. No VLESS UUIDs, subscription URIs, credentials or full configs in logs or repository.
Tests for each node must bind to a dedicated isolated Xray outbound. Bare ICMP from the router cannot prove the selected VLESS route; any ICMP readings must be explicitly labeled with their actual routing path.

## Architecture
- Bounded, read-only probe runner with resource limits; cannot take over active SOCKS 10808 or TPROXY 12345.
- Mini-PC holds durable historical telemetry (e.g. SQLite or compatible supported stack).
- Mosquitto MQTT integration sends summary sensors to HA with restricted credentials, LAN-only ACL, no port forwarding.
- HA dashboard for node state, latency, success rate, egress IP changes, incidents and 24-hour/7-day/30-day trend.
- Keep a local buffer if HA/MQTT offline; monitoring errors must not disrupt live traffic.

## Delivery gates
P0: read-only discovery of network and supported HA OS Apps; verify backups and accessibility.
P1: offline source and automated tests for stable identity, safe probe isolation, fail-closed checks and sample payload/schema.
P2: explicit approval for read-only router canary and service installation.
P3: explicit approval for MQTT/HA sensor integration, retention and alert configuration.
P4: optional recommendations for VPN pool changes; no auto-pool modification, daemon restart, firewall/routes/cron/watchdog changes, merge, deployment or seamless cutover without distinct approval.

## Acceptance
Per-node route provenance confirmed, subscription reordering preserves node ID, monitoring failure cannot affect live Xray, HA graphs reflect actual measured results, alert thresholds and timestamps testable, rollback documented.

## Current state
Documentation only. No production Keenetic changes; no mini-PC or Home Assistant changes; no credentials collected or stored. See library /Keenetic/VPN-Monitoring for matching project overview.