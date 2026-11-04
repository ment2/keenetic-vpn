# OpenAI MQTT monitoring follow-up, 2026-11-04

## Done
- Owner locally ran the first OpenAI collector cycle with --publish and --max-cycles 1. Seven states reported (vpn01/02/04/05/09 reachable; vpn06/07 network_error).
- Verified on router: /opt/var/lib/vpn-monitor/openai/history.jsonl has seven JSONL records and no persistent OpenAI monitor process remained.
- Existing code sends 21 retained HA MQTT discovery configs (3 per 7 nodes) before seven states; no sender exceptions reported. This confirms sender-side delivery, NOT HA entity registry creation.
- Private home-assistant-control plugin plugins_6aeb33fb5ed48191b710e58b188e5b1f v0.1.0 exists; MCP URL declared but its tools have not been made available to this chat (API-key connection still required). Cannot verify recipient registry through current connector set.
- Read-only Keenetic cron check: 27 total lines, no OpenAI collector schedule. The prior general VPN Health collector runs separately and is unaffected.
- Hardened OpenAI status normalizer maps child Xray startup failure to unreachable, other http_* to http_error; CI 41872167433 SUCCESS. Router module /opt/tmp/vpn-monitoring-lab/monitoring/openai_health_contract.py update done job ecfb8bb6-3e30-407b-9f37-b3aac61a1837, sha256 7af0e3efd5b37bf04c13d371a858066643a073fc44e5cb3b735d4310d53ebbc9, backup true.
- Added bounded history rotation (2 MiB + up to three retained backups, rejects symlink paths) to OpenAI collector and tests; CI 41873235903 SUCCESS. Router module /opt/tmp/vpn-monitoring-lab/monitoring/openai_health_collector_loop.py update done job e6dd2777-8e0f-4aeb-b181-d15306bfb61b, sha256 695978d642a360248fc0ab3706cc389830448acdaef9ded0c4f0f0a556aa3718, backup true.

## Still not done
- No direct Home Assistant entity registry verification for the 21 newly sent sensors.
- No permanent cron schedule or supervisor enabled; existing remote exec for MQTT publication was blocked by OpenAI safeguard, so do not bypass by indirect execution or scheduling.
- No production Xray, firewall, route, legacy collector or mainline branch changes.

## Next action gate
Connect the already created private home-assistant-control plugin through its bearer API-key flow so read-only Home Assistant verification can be performed. Alternatively owner can inspect MQTT entities in HA UI. Once validated, the standalone one-shot collector could be scheduled every 15 minutes through a separately authorized local deployment procedure, with root-only MQTT credentials handled solely on router. Verify live schedule and stale entity expiration after setup.
