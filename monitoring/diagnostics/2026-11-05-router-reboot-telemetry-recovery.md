# Keenetic reboot recovery: monitoring services (2026-11-05)

## Scope
Owner requested recovery and documentation after a Keenetic reboot. Read-only inspection identified two telemetry collectors missing after restart; production Xray, Telegram bot, Keenetic Agent, Cloudflare Sync and watchdog were already running. No production Xray, routing, firewall, kill-switch, Telegram or existing cron changes were made.

## Evidence before repair (MSK)
- Router at 19:51 was online, around 10 minutes uptime. Production Xray PID 815; SOCKS 127.0.0.1:10808 and TPROXY :12345 listening.
- Bot assistant.py PID 906, memory_bridge.py PID 751, Keenetic agent PID 2405; Cloudflare sync and both Xray watchdog processes present.
- 60-second traffic collector process absent; collector.log last update Nov 5 19:28.
- 15-minute VLESS health collector process absent; vpn-health.log last update Nov 5 19:20.
- OpenAI 15-minute cron at root crontab line 31 remained configured and refreshed /opt/var/log/vpn-openai-health.log at 19:45. MQTT broker 192.168.0.169:1883 and HA :8123 reachable from router.
- Independent OpenAI probe: vpn01, vpn02, vpn04, vpn05, vpn09 reachable; vpn06/vpn07 network_error. General VLESS monitoring is NOT an OpenAI reachability test.
- HA screenshot displayed all seven general VLESS sensors unavailable and HA Agent Monitor BLOCKED / Cloudflare disconnected / last poll yesterday. HA Agent Monitor is a separate Home Assistant-side component; Keenetic Agent was verified live.
- Cloudflare sync log contained intermittent URLError [Errno 131] Connection reset by peer, with subsequent normal zero-work polls.

## Root cause and safe remediation
Existing collectors in /opt/tmp/vpn-monitoring-lab were started manually, without boot integration. First recovery attempt used nohup, which does NOT exist on this BusyBox; it exited without launching children (job 7c893d70-d983-485b-af80-d8817ec430d2). BusyBox start-stop-daemon is available at /opt/sbin/start-stop-daemon with -S, -b, -d, -p, -m, -O; confirmed by tool job eaa0a2f1-dfbe-43b7-bbfe-608cac636d14.

- Started collector with start-stop-daemon. Job f79ddbab-e734-4358-bef5-929954206076 done exit 0: traffic PID 4453, health PID 4456.
- New traffic CYCLE_OK 1 with reset (baseline after reboot), followed by CYCLE_OK 2 and 3 with all three interfaces ok.
- New VLESS HEALTH_CYCLE 1: all seven tags returned ok (vpn01, vpn02, vpn04, vpn05, vpn06, vpn07, vpn09).
- Created /opt/etc/init.d/S99zz-vpn-monitoring from repository source monitoring/scripts/S99zz-vpn-monitoring, mode 0755; shell syntax passed; SHA256 abea4530831916ddc92eac4742a5f9a528a3efc4188a9e13f3305cc4a3d855af. Install job 30ac2009-ae31-4b98-b659-58aa9ec3e5a9 done exit 0.
- Idempotence job ecbd69bb-e390-4d03-94e5-0d366eba34c8 done exit 0: traffic already running / health already running; exact process counts 1 and 1. No restart of active processes.
- Two distinct PID files, existing Python fcntl single-instance flock safety, SIGTERM handling and log paths retained.
- MQTT password was only checked for existence; secret content was not read, printed, transferred or committed.

## Remaining verification and problems
1. HA Agent Monitor BLOCKED is NOT yet repaired or attributed. Needs HA host-side integration/agent state and credential-free log checks through appropriate HA management access.
2. General VLESS MQTT sensor updates should be observed in the HA UI after first successful publication. Router logs show HEALTH_CYCLE ok but do not alone prove HA state refresh; test current sensor attributes/timestamps.
3. Cloudflare sync has transient connection reset events, not yet root-caused.
4. OpenAI route checks show vpn06/vpn07 network_error (separate from general VLESS health).
5. No deliberate reboot was performed to acceptance-test new startup script. Boot integration is installed and syntax/idempotence checked, but actual reboot-once startup is not proven.
6. No per-VLESS user traffic attribution is enabled; apclii0/br0/br1 are interface counts and should not be summed as unique VPN traffic.

## Safety / rollback
No Xray/firewall/routes/cron/watchdog/bot changes. To disable only this boot hook, move /opt/etc/init.d/S99zz-vpn-monitoring outside init.d or remove executable bit; for controlled stop, use /opt/etc/init.d/S99zz-vpn-monitoring stop (PID and process cmdline checked before SIGTERM). Never killall Python or Xray. Current boot hook starts only the monitoring Python collectors.

## GitHub
Repo: ment2/keenetic-vpn
Branch: feature/vpn-monitoring-home-assistant-20261104
Startup script commit: 0fd5e9d2591d7f0105863c352c25f03c5e5a923d

## Keenetic jobs
- discovery/verification: 921c2738-853d-47ac-9b54-c1f692ac1815, 66762b58-05af-4588-aeb2-08a5e307ea7c, b4dd0658-92bc-456e-b18e-45bb7e4e120f, 2bca34a3-650f-4abe-9ea7-2a9cefa05c16
- failed nohup: 7c893d70-d983-485b-af80-d8817ec430d2
- daemon capability: eaa0a2f1-dfbe-43b7-bbfe-608cac636d14
- successful start: f79ddbab-e734-4358-bef5-929954206076
- startup install: 30ac2009-ae31-4b98-b659-58aa9ec3e5a9
- idempotence check: ecbd69bb-e390-4d03-94e5-0d366eba34c8
