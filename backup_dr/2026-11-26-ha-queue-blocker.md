# Backup DR v3.1 — HA queue incident, 2026-11-26

Backup candidate baseline: ment2/keenetic-vpn commit 138e1b65fd982f3f8e55c975e15351a889d4011d. Previous offline acceptance 26/26, not rerun here.

## Observed evidence
- HA listener job ca8cb67a-b25d-4566-b3ec-712acbdade18: queued, no claim in HA audit.
- HA diagnostic da504b6d-3080-4935-a45f-44b1a2bd0a14: queued, no claim.
- Last successful HA job 7c7777dc-eac6-4022-9a69-a1ce5486120b: write_file result received; later OAuth refreshed. Remote enabled, owner_admin enabled, revision 3.
- Cloudflare homeassistant-control-bridge health: ok=true, HA_ADDON_ROOT_NOT_HA_OS_ROOT.
- Repository ment2/keenetic-control branch feature/homeassistant-admin-agent-20261104, agent/homeassistant/ha_monitor.py blob 71d62fe1b7097c1cc7f2e0019a7de238fc7914e6: 30s poll, fail-closed on unknown tick errors, pending journal blocks start. Historical recovery 2026-11-05 documented analogous BLOCKED status, not proof of same cause today.
- Browser alternate access unavailable: originating browser context required. No independent authenticated shell available through HA MCP because it uses the same queue.
- Keenetic LAN probe job 89fb2172-6467-431a-b7b4-ab88fe23f7ca submitted; status queued at first check.

## Recovery gate
From HA Advanced SSH add-on terminal (not Keenetic), run `python3 /data/ha-admin-agent/ha_monitor.py status`. If NOT_RUNNING and PENDING_JOURNAL False, inspect redacted status/detail and explicitly start with `python3 /data/ha-admin-agent/ha_monitor.py start`; check status after 5s. If pending exists, do not delete, restart or re-execute; reconcile against audit. Do not display token or journal content. If running but stale, inspect monitor state and process without killing. Do not restart HA Core, change firewall or OAuth policy.

After queue claims resume, do not duplicate queued listener. Confirm readiness before rerunning fixture sender (previous sender job c8d47e20-a6a6-4846-a0f6-e25b5c521f74 failed connection refused). Confirm authenticated receipt and SSD restore, then proceed to production gates. No production backup created or service changed in this incident step.