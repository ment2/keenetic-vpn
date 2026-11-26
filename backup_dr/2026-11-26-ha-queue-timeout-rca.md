# HA queue timeout head-of-line incident — 2026-11-26

Backup DR baseline: b9831e232ddb33885b8a9179de91faac081c35ef, v3.1. No production changes.

## Evidence
- Owner's HA terminal: MONITOR_PROCESS=RUNNING, PENDING_JOURNAL=False, STATUS=RUNNING, DETAIL=HA_AGENT_IDLE, POLLS=335, UPDATED_AT=1795718758.
- HA listener job ca8cb67a-b25d-4566-b3ec-712acbdade18 was submitted with timeout=145 seconds. Created 18:36:20.783 UTC. Still queued. Diagnostic da504b6d-3080-4935-a45f-44b1a2bd0a14 is queued behind it. Audit has no claim for either. Prior sender failed connection refused.
- Reviewed ment2/keenetic-control, docs/ha-control-work-recovery-20261126, docs/homeassistant/2026-11-26-ha-oauth-release.mjs, blob df83f16082835e8980838aeb45616aef3d1f9936: lines 266–273 select FIFO head before checking exec_timeout; lines 359–363 default agent cap to 45 unless explicit 180 header; lines 156–166 expire queued jobs after 3600000 ms. HA agent source does not send 180-capability header; HA command implementation caps at 45. This is a strong source-based RCA, not a byte-for-byte comparison with current deployment. Latest Cloudflare deployment reports be38dd8c-7777-45c9-9b92-8cb407c79d1d; reviewed release is historical.
- Expected expiry of blocked listener: 19:36:20.783 UTC (21:36 Bucharest/22:36 Moscow); next agent poll should mark it failed and claim compatible diagnostic, if no other blocker. This has not happened yet.

## Safe recovery
No restart, policy revision change, token rotation, or Worker deployment needed for natural expiry. Existing public HA MCP has no cancel-queued operation; owner policy POST would invalidate all queued jobs and is disproportionate without separate approval. Do not send unsupported jobs. Poll existing IDs, confirm diagnostic completion, then launch a bounded isolated fixture listener via a short command (<=45 sec) with detached child, explicit unique PID/lock, finite lifetime and readiness marker. Confirm actual listener on 8765 before sender. Use only synthetic key/data. Real production backup remains off.

## Durable correction candidate
HA-specific ingress should reject exec timeout outside 1..45 before enqueue, expose actual supported max in tool schema, and return a clear error for unsupported legacy head instead of silently reporting idle; preserve strict FIFO and all uncertain-execution/recovery gates. Do not deploy from historical source; first compare exact active release and review the change. Model tests in test_ha_queue_timeout_model.py cover head blocking, expiry, and guard. These are isolated predicate tests, not Worker integration or live acceptance.