# Home Assistant OpenAI MQTT first cycle verification, 2026-11-04

## Local user-approved publish
Owner ran directly on Keenetic via Termius:
`cd /opt/tmp/vpn-monitoring-lab && PYTHONDONTWRITEBYTECODE=1 /opt/bin/python3 -B -m monitoring.openai_health_collector_loop --max-cycles 1 --publish`
The process exited normally and printed:
OPENAI_CYCLE 1 [('vpn01','reachable'),('vpn02','reachable'),('vpn04','reachable'),('vpn05','reachable'),('vpn06','network_error'),('vpn07','network_error'),('vpn09','reachable')].
In current code, the first --publish cycle calls publish_for_inventory() for 7 nodes x 3 MQTT Discovery sensor configs = 21, then publishes 7 state payloads. It raises/catches MQTT exceptions, and would return per-node error: if state publish failed. All 7 returned measured status. Therefore router-side first delivery likely succeeded and 21 retained discovery configs were sent. Direct Home Assistant entity registry verification is NOT yet available. No direct Home Assistant MCP tools in currently connected runtime.

## Independent read-only router verification
Job d01cf1d8-48ab-46ab-85fd-4aac5f432378 done exit_code=0; history file /opt/var/lib/vpn-monitor/openai/history.jsonl exists, HISTORY_ROWS=7 with expected seven unique tags and statuses:
- vpn01, vpn02, vpn04, vpn05, vpn09 reachable / route_verified true
- vpn06, vpn07 network_error / route_verified false
No currently-running openai_health_collector_loop process. This is expected for --max-cycles 1.
Production Xray, routing, firewall, cron and existing 28 VPN Health sensors unchanged.

## Remaining action
Directly verify expected 21 MQTT Discovery entities are present and updating in HA before persistent scheduler setup. Avoid claiming that HA registered all entities from sender-only evidence. User prefers no manual intervention. Credentials not read or transmitted via remote tool, and earlier remote exec attempt requiring MQTT password was blocked by tool safety; no bypass. A permanent launcher may be staged offline but should not be enabled until HA verification and explicit scope on persistent autostart are satisfied.
