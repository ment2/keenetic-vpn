# HA watchdog production activation — 2026-11-26

Baseline documentation: ment2/keenetic-vpn commit 71426b24c652599c1e7c3fed076d034b43de246a. The owner reported saving the edited SSH add-on init_commands and restarting the add-on. This activation was performed by the owner, not remotely by ChatGPT. Previous isolated acceptance: 18/18 and 43.018 s full-budget test; installed runtime verification: 6/6 hashes and import PASS.

Fresh independent HA MCP exec job 79b637ff-790f-4374-aad8-e843d4fdd874 (timeout 15 s, created 2026-11-26T20:56:49.814Z) completed exit 0. Actual output:

```text
OLD_AUTOSTART False
NEW_AUTOSTART True
EXPORT_PRESENT True
PROCESSES [('454', 'ha_monitor_watchdog_candidate.py'), ('521', 'ha_bridge_tick.py')]
CANDIDATE_HASH 22ba0f5d070d21b38dd47cadc2b35316fe39d81cd1ab2ea46adb00489bf12b08
MONITOR_PROCESS: RUNNING
PENDING_JOURNAL: True
STATUS: RUNNING
DETAIL: HA_AGENT_IDLE
POLLS: 7
UPDATED_AT: 1795726578
```

Cloudflare audit confirmed queued, claimed, result_received for that same job at policy revision 4 (result_received 1795726614418). Pending journal presence was observed during execution of this diagnostic; it is not evidence of an unresolved receipt. Idle journal absence has not independently been measured. No old monitor process in the reported process scan; the tick child is expected. Current installed candidate hash matches reviewed release. Autostart and add-on Watchdog toggles were visible enabled in earlier user screenshots. This is actual startup after an add-on restart, not a full HA OS reboot test.

Follow-up status-only job 0e180d54-32a2-4ccc-9852-bcefdb1d7391 (timeout 10 s) submitted once, created 2026-11-26T20:57:16.053Z. No repeat submissions. Completed exit 0: MONITOR_PROCESS RUNNING, PENDING_JOURNAL True during own execution, STATUS RUNNING, DETAIL HA_AGENT_JOB_ACKNOWLEDGED, POLLS 8, UPDATED_AT 1795726614. Audit queued/claimed/result_received confirmed at revision 4, result_received 1795726649621. Two successive live commands completed and polls advanced 7 to 8.

Limits: production Worker 54 exact repeat-result idempotency remains unattested; no deliberate duplicate submission, no retry of uncertain command, no source-filter bypass. Candidate addresses receipt recovery and bounded retry, not every possible URLError after claim. Do not equate live normal execution with proof of recovery under every production fault. No HA or Cloudflare setting was modified by ChatGPT in this turn. No Keenetic calls, real backup, or restore. Previously blocked Keenetic transfer remains blocked. Preserve the old monitor files and rollback startup command; any rollback must wait for clean queue/journal/locks in independent local maintenance context.
