# OpenAI VPN monitoring offline stage
Date: 2026-11-04. Branch: feature/vpn-monitoring-home-assistant-20261104.

## Verified baseline
Owner confirmed seven VLESS nodes, 28 HA MQTT entities and router collector PID 8448. VPN health cycles 6-20 showed nine generic egress failures on vpn06 out of 15 checks. These tests are not OpenAI service qualification.
The router OpenAI probe script xray_openai_probe.py has check(outbound) at line 16. The implementation and return schema remain uninspected. Existing read-only job b3953233-dda7-41c0-ab9f-0e8395cccb4a is QUEUED, and must not be resubmitted.

## Prepared and CI-verified
monitoring/openai_health_contract.py: success only for explicit reachable with verified route; unknown outcomes fail closed; no RTT label.
monitoring/openai_health_discovery.py: 3 new MQTT sensors per node (status, checked_at, full duration), 21 total, stable node ID shared with existing HA device.
monitoring/tests/test_openai_health.py: strict return sanitation, positive-evidence requirement, fail-closed, retained discovery and safe metadata.
CI 41856507749 SUCCESS at 7a8b075562b46740d132364dc522c39daaad4ec7.

## Deployment gate
Wait for that exact read_file job, inspect check(outbound) timeouts, actual return data, isolated child lifecycle and process/resource bounds. Build tested adapter and 15-minute collector only after inspection. Router-side MQTT password stays local and must not be retrieved by the assistant. Do not touch production Xray, routes, firewall, cron, watchdog, automatic cutover or current VPN health collector.
No live OpenAI monitoring has been enabled yet.