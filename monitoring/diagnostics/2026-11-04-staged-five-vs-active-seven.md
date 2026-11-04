# 2026-11-04 OpenAI qualification: definitive cause of RU nodes in live Xray pool

After user questioned RU servers, read-only investigation and on-demand OpenAI checks confirmed:
- Active production config includes 7 VLESS: vpn01, vpn02, vpn04, vpn05, vpn06, vpn07, vpn09.
- VLESS HTTP-egress checks returned success for all 7, but this is not OpenAI qualification.
- Independently, current `/opt/bin/xray_openai_probe.py` returned `network_error` for vpn06 (6.03 s) and vpn07 (12.08 s), via job a1a43e66-3b9b-440b-ae2f-49bae6c7c4b1.
- The active hourly updater `xray-safe-hourly.sh` calls `xray-update-v23.py`, which adds to `allowed` only after `check_openai(outbound) == 'reachable'`.
- Most importantly: the Xray update log (read-only job 59ce2b59-845c-4a3d-b084-3aef9dcd1122) shows the candidate **already correctly filtered**:
  vpn01 ALLOWED DE; vpn02 ALLOWED NL; vpn04 ALLOWED DE; vpn05 ALLOWED DE; vpn09 ALLOWED US;
  vpn06 API_NETWORK_ERROR RU; vpn07 API_NETWORK_ERROR RU; some iterations also reject vpn11 HK.
- The log reports `ALLOWED: 5`, `POOL: vpn01, vpn02, vpn04, vpn05, vpn09`, `FALLBACK: vpn01`, and `PENDING_UNCHANGED: verified candidate staged; NOT applied` for repeated runs on 2026-11-04 including around 12:31, 12:46 and 13:01 router-local time.
- Therefore the cause of RU outbounds remaining in *active* Xray is not failure of the eligibility filter: the safe staged candidate is intentionally **not activated**. Production remains on older seven-outbound config.
- This means Xray's leastPing observatory may still route normal traffic through the RU outbounds, where OpenAI currently fails. Health monitoring must show separate `vless_egress` vs `openai_reachable` statuses and flag active-vs-approved-pending divergence. Never claim all 7 are OpenAI-qualified.

Safety: do not force-apply candidate, alter production Xray, restart processes, or change fallback until the existing seamless cutover HARD NO-GO constraints are separately resolved and the owner explicitly approves a safe transition. The active Xray and other production services were not changed during this audit.
