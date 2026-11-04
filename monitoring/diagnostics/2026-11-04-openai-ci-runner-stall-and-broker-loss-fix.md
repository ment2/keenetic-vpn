# OpenAI monitoring stage: CI runner unassigned and MQTT offline persistence
Date: 2026-11-04
Branch: feature/vpn-monitoring-home-assistant-20261104.

## Applied offline fixes
- Normalize nonstring/unhashable status to unknown without crashing or leaking arbitrary user/probe data.
- OpenAI route_verified is positive only when existing isolated Xray probe observes explicit reachable (curl HTTP 401).
- OpenAI collector records sanitized probe result to root-only JSONL BEFORE MQTT delivery, retaining evidence if broker is unreachable. Tests cover broker failure, missing password, bad status, exception and no default publication.

## Deployment gate
- Existing production Xray and router VPN-health collector remain unchanged.
- Existing GitHub Actions ubuntu-latest workflow jobs have status queued with runner_name=null and empty steps. Latest run 41865332989 at e352d318d17826978c53787fa17e74aeaa7f66af was queued at observed time; no claim CI passed. Older contract/discovery CI 41856507749 SUCCESS is not proof new collector passed.
- A root deployment requires exact approved write destinations and command under Keenetic Mobile tool policy. Do not equate general project permission with authorization for unknown commands.
- Once CI SUCCESS, deploy separate files into /opt/tmp/vpn-monitoring-lab/monitoring only via audited exact operations, run single --max-cycles 1 dry mode without --publish first, confirm no child Xray linger, then publish 21 Discovery+states using router-local password, and schedule controlled collector only after verification.
- Do not install or activate while CI queued; never restart production Xray, alter firewall, routes, cron, or global killall.