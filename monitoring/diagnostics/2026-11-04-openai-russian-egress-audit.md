# Incident: RU egress nodes fail OpenAI despite working VLESS (2026-11-04)

Scope: `ment2/keenetic-vpn` feature branch `feature/vpn-monitoring-home-assistant-20261104`. Router findings from read-only inspection and independent per-outbound probes.

## Findings
- Active Xray config contains `vpn06` and `vpn07`, both VLESS outbounds. Previously an isolated generic IP-echo probe returned status=ok with exit IPs:
  - vpn06 `178.72.144.171`, geolocation code RU
  - vpn07 `95.129.234.51`, geolocation code RU
  This merely proves egress HTTP connectivity, NOT OpenAI eligibility.
- Owner correctly questioned these nodes in an OpenAI-qualified pool.
- Task `a1a43e66-3b9b-440b-ae2f-49bae6c7c4b1` invoked the pre-existing `/opt/bin/xray_openai_probe.py` check on current individual outbounds:
  - `vpn06 OPENAI_CHECK network_error ELAPSED_S 6.03`
  - `vpn07 OPENAI_CHECK network_error ELAPSED_S 12.08`
- Actual active updater `/opt/bin/xray-safe-hourly.sh` references `/opt/bin/xray-update-v23.py`. Read-only AST inspection confirmed that v23 calls `probe(outbound)`, then `check_openai(outbound)`, and appends to `allowed` ONLY if `api_status == 'reachable'`. If all fail, candidate validation is skipped. The OpenAI-specific check is stronger than the IP echo check.
- Active config still lists the two tags because the qualification filter is applied at candidate construction time, not continuously inside the already-running Xray; root cause of old inclusion or failure of recent update is pending log audit. No claim those nodes previously qualified.
- Relevant risk: Xray `leastPing` selector uses `observatory` HTTP connectivity, not necessarily OpenAI service health. It can route new user traffic over an outbound where OpenAI currently fails.

## Monitoring correction
The initial seven-of-seven generic egress report must be explicitly labeled `vless_egress_ok` and NOT `openai_qualified`. Maintain separate fields: egress route witness, OpenAI reachability, validation time, and unknown/error states. No current per-outbound usage telemetry via the disabled Xray stats API.

## Safety
No live config, Xray PID, watchdog, cron, firewall, routes, or fallback modified in this audit. No production changes without a separate plan and explicit authorization, especially considering the hard NO-GO for seamless production cutover. Avoid disabling servers based solely on outdated or country-only geolocation. Follow up with update log examination and repeatable independent OpenAI probe evidence.
