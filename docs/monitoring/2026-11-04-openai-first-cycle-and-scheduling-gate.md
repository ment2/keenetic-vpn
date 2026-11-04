# OpenAI health monitoring: first MQTT cycle and scheduling gate

Date: 2026-11-04. Repo: ment2/keenetic-vpn, branch feature/vpn-monitoring-home-assistant-20261104.

## Verified live
Owner ran one local command from Keenetic Termius with `--max-cycles 1 --publish`, which returned normal `OPENAI_CYCLE 1` output for seven tags. Router read-only verification task d01cf1d8-48ab-46ab-85fd-4aac5f432378 completed exit 0: `/opt/var/lib/vpn-monitor/openai/history.jsonl` contains exactly seven results. 5 reachable (vpn01,vpn02,vpn04,vpn05,vpn09), 2 network_error (vpn06,vpn07); no OpenAI collector process after one-shot. Sender code first publishes 7×3 MQTT Discovery and then 7 state messages, without throwing any error in run, but HA registration remains unverified.

## Later hardening
Source commit 84b715d6e6ec15b49829f44d63104c67780d4a82 maps xray_start_failed to unreachable and unexpected http_* to http_error; additional test commit a2f95657f0a33107de256ae127cf335f5535e402. CI runs 41872090385 and 41872167433 BOTH SUCCESS. Only updated `/opt/tmp/vpn-monitoring-lab/monitoring/openai_health_contract.py` on router via Keenetic Mobile write_file ecfb8bb6-3e30-407b-9f37-b3aac61a1837 DONE exit 0, sha256 7af0e3efd5b37bf04c13d371a858066643a073fc44e5cb3b735d4310d53ebbc9, backup true.

Read-only crontab inspect exec job 8c05e2d2-4614-4ed9-a5ca-9293aa79c43b DONE exit 0:
- CRON_READ_CODE 0
- OPENAI_MONITOR_CRON_LINES 0
- GENERIC_HEALTH_CRON_LINES 0
- TOTAL_CRON_LINES 27.

## Connection limitation
Private personal Plugin Creator plugin ID plugins_6aeb33fb5ed48191b710e58b188e5b1f exists as home-assistant-control v0.1.0, with configured MCP URL `https://homeassistant-control-bridge.wlad124650.workers.dev/mcp` and bearer API-key auth in private manifest. Its callable Home Assistant tools are NOT connected/available in this ChatGPT run. Plugin existence alone is not proof of authorization or server reachability; do not claim HA registry entities verified.

## Proposed schedule (NOT INSTALLED)
Only after HA entity verification and owner-authorized local credential handling, use existing module with one bounded cycle each 15m:
`*/15 * * * * cd /opt/tmp/vpn-monitoring-lab && PYTHONDONTWRITEBYTECODE=1 /opt/bin/python3 -B -m monitoring.openai_health_collector_loop --max-cycles 1 --publish >> /opt/var/log/vpn-openai-health.log 2>&1`.
Collector owns separate nonblocking fcntl lock, local root-only password, and isolated Xray subprocesses; never restart production Xray or mutate routes. Configure log rotation and retention as followup before permanent enabling. Avoid reexecuting via remote tool a command that was safety-blocked for reading local MQTT secret. Do not install cron by indirect workaround.

## Next independent tasks
- Obtain Home Assistant Control plugin connection to read exactly 21 expected MQTT entities and verify fresh state timestamps, without revealing tokens.
- Document safe log rotation and MQTT offline alert behavior.
- Schedule recurring one-shot collection only once proper authorization is available; don't claim continuous monitoring before it is started.
