# Keenetic Xray v27: batch 3 and seamless pool architecture

Date: 2026-10-30. No router mutations performed.

## Read-only job results
All done, exit_code 0:
- e438cf68-e7d1-48e3-875b-e10af304fd97: `/opt/bin/xray-update-v23.py`
- 82b6337c-4852-4033-b71c-b521db565d2e: `/opt/bin/xray_openai_probe.py`
- e550fc0f-c39f-46c7-b8b7-0f20825222d5: `/opt/bin/xray-safe-hourly.sh`
- 0ced0f24-936b-4780-b49b-0dced9b23797: `/opt/bin/setup_xray.py`
- aeef051e-d48a-4270-9861-271f7376e6e8: `/opt/bin/update_xray_subscription.py`

## Confirmed implementation
`xray-update-v23.py` downloads HTTPS subscription, parses VLESS, calls `xray_server_check.probe` then `xray_openai_probe.check`, admits only `reachable`, builds config with VPN-only outbounds plus blackhole, `leastPing` balancer, validates `xray run -test`, optionally writes a new candidate file. Server tags `vpnNN` are ordinal and unstable if subscription order changes. `xray_openai_probe.py` launches isolated temporary Xray on ephemeral localhost SOCKS port, checks OpenAI API /v1/models expecting HTTP 401, terminates its own process. `xray-safe-hourly.sh` generates, validates and atomically stages pending config, no production restart. `setup_xray.py` main routine writes config.json and includes a direct/freedom outbound: DO NOT execute its main routine on production. `update_xray_subscription.py --apply` replaces config.json; DO NOT invoke for seamless deployment.

## Design direction, not yet implemented
1. Retain existing read-only staging and OpenAI qualification, add stable identity by normalized outbound fingerprint (no credentials in logs or reports).
2. Introduce immutable versioned pool snapshots and compare normalized contents; recheck candidate immediately before promotion.
3. Separate permanent ingress/front-end from replaceable outbound pool backends. An isolated candidate backend must bind unique ports and must not share production inbound ports. Verify Xray-specific routing and connection draining feasibility before selecting blue-green design.
4. Candidate backend starts isolated and is probed through its own SOCKS; never use `S97xray restart` or `killall xray`. Maintain previous backend to drain existing flows; new flows routed to promoted backend only after verification. UDP requires explicit session mapping/timeouts, so zero interruption cannot be guaranteed before testing.
5. Preserve existing TPROXY and SOCKS entrypoints and provider fail-closed semantics; no `direct`/`freedom` fallback. Fail safely if old watchdog can restart/kill all Xray processes. Build explicit rollback for new connections and avoid terminating live sessions.
6. Before any production changes: review actual kernel/port routing capabilities, old watchdog activity, and run isolated non-production simulation. No router modifications are authorized by this document.

## Open questions
- Whether Xray API supports sufficiently granular outbound update in deployed version without losing existing sessions.
- How a stable ingress forwards TCP/UDP flows to pool backends without direct provider fallback.
- How to neutralize old watchdog restart behavior safely during an eventual approved migration.
- How to verify fail-closed behavior and drain UDP/TCP sessions in controlled tests.

## Archiving
After production launch, store exact final deployed source versions, redacted config structure, SHA256 checksums from actual bytes, rollout and rollback records in `/Keenetic/Xray/`. Never archive subscription URLs, credentials, UUIDs or private keys.