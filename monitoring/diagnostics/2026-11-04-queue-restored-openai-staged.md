# Queue recovery verified; isolated OpenAI monitor staged

Date: 2026-11-04.

## Queue recovery
Owner explicitly authorized single acknowledge_unknown_no_reexecute for exact exec ID 26e5412c-628c-4f75-ae0a-514b7fa47ddd with unknown outcome accepted. Owner directly executed preflight and single authenticated POST /v1/owner/reconcile and reported HTTP 200 {"ok":true}. Exact job transitioned unknown -> failed, exit_code=-1. Original command was not retried. No Xray/routes/firewall mutation.
Queued read_file b3953233-dda7-41c0-ab9f-0e8395cccb4a became done exit_code=0 afterward. This confirms queue -> agent -> result flow recovered.
## Actual /opt/bin/xray_openai_probe.py
The returned file shows check(outbound): creates temporary Xray config with SOCKS5 inbound on random 127.0.0.1 port, routes it to precisely one original VLESS outbound with changed probe tag, starts separate Xray child, runs curl through socks5h:// loopback to https://api.openai.com/v1/models, declares reachable only if curl exits 0 and HTTP=401; returns network_error, timeout, xray_start_failed, or http_CODE for other cases. Finally terminate/wait child with kill/wait fallback. Does not change active Xray config or process. Distinct OpenAI health versus generic egress route witness. Whole source verified by completed remote read.
## Offline GitHub deliverable
- openai_health_contract.py and openai_health_discovery.py already staged with unit tests and CI SUCCESS 41856507749.
- openai_node_probe.py loads existing installed check and returns sanitized telemetry, positive route witness only on reachable.
- openai_health_collector_loop.py independent 900-second serialized per-node monitor, local MQTT credential read, 21 discovery messages, separate journal and flock.
- test_openai_health_collector.py covers failure, exception redaction, route witness, MQTT and no publisher by default.
- Latest CI run 41864348846 on d11623824a12a9ae971b0e35538fa39a93546feb is queued as of observation; do NOT label stage CI-success until complete.
## Live deployment
Not deployed; no new OpenAI sensor claims. The installed main health collector and active Xray untouched. Any root write/exec installation must have exact operation authorization in addition to general project permission per tool contract. 
