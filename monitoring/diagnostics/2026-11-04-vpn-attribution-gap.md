# 2026-11-04: VPN-specific attribution and health observation

Owner asks how to identify which VPN carried traffic and which VPN had the problem. Current interface counter collector measures Linux `apclii0`, `br0`, `br1` RX/TX only. These metrics cannot attribute sessions or bytes to individual Xray VLESS outbound tags.

Read-only Keenetic task 84fad30b-df02-4836-b714-188bd8243625, exit 0, inspected only public structural configuration fields (no secrets):
- Active VLESS outbound tags `vpn01`, `vpn02`, `vpn04`, `vpn05`, `vpn06`, `vpn07`, `vpn09`; `blocked` blackhole outbound.
- Balancer tag `auto`, selector `vpn`, fallbackTag `vpn01`, strategy `leastPing`.
- `api`, `stats`, `policy` all absent. Precise per-outbound traffic usage is **not available** in existing stats instrumentation.

Read-only task e3e527c9-0e1b-4e96-a9fb-aac178bfaed5, exit 0:
- `observatory` is configured, subjectSelector `['vpn']`, probeInterval `60s`, relevant keys `enableConcurrency`, `probeInterval`, `probeUrl`, `subjectSelector`. No burstObservatory.
- Existing scripts `/opt/bin/xray_openai_probe.py`, `/opt/bin/xray_server_check.py` exist; do not execute, modify or disclose credentials without separate audit.

Plan:
1. Read-only audit existing probe script behavior/output safety and whether Xray observatory results are externally accessible without API/config changes; use stable endpoint-derived identifiers, not tag-only.
2. Add per-outbound health sensors (online, probe latency, failure reason, last success) with independently verified execution route, without claiming a balancer probe shows actual selected path.
3. Attribution of actual traffic or real user sessions to specific VPN requires explicit real instrumentation (Xray outbound counters/flow logs/conntrack mappings), controlled configuration changes and a separate approved lab/production rollout, not interface-counter arithmetic.
4. Preserve working VPN and established safety gates. Do not alter Xray, firewall, routing, cron, watchdog or existing sampler as part of diagnosis.

Owner confirmed first MQTT HA discovery 12 PUBACK, first and second telemetry cycles PUBACK, and then successful startup of 60-second collector (PROCESS_RUNNING/CYCLE_OK per owner). Automatic start after router reboot not enabled; HA device registration still not explicitly observed.
