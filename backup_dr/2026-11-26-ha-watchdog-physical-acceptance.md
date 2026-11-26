# HA watchdog — isolated physical acceptance, 2026-11-26

Baseline: ment2/keenetic-vpn commit 5580794e1cddade2e8e0a2e9989db75f86da4078; local-only handoff documentation commit 8786b696c39472fdc63c1f6665427025ee6ed43c. Owner subsequently authorized direct HA MCP transfer of the isolated fixture and test execution. No use of Keenetic, no bypass of a rejected tool operation, no production deployment or policy/token change.

## Physical transfer and integrity

Directory /tmp/ha-watchdog-acceptance-5580794 created with root ownership and mode 0700, job d1795b0b-c9d5-40b0-aa65-dc5b8d21b218, done exit 0. HA MCP accepts text; the eight package members were individually transferred using the normal write_file operation (not binary ZIP transport). Every write was acknowledged FILE_WRITE_SHA256_VERIFIED, exit 0:

| File | Job ID |
|---|---|
| manifest.json | 34a1eef7-00b9-4b44-8647-e382291a892e |
| ha_receipt_retry.py | e455a8c2-c555-42c5-ba89-9f29061f03b3 |
| ha_monitor_receipt_candidate.py | 6ef2f774-fa03-46ce-bdb8-4c7fe171e9cb |
| ha_receipt_watchdog.py | 2d4aee7e-435e-485c-a273-ad7099ea9358 |
| ha_monitor_watchdog_candidate.py | b0e91521-a5dc-4fcd-ac6e-77b5a7dcb113 |
| test_ha_receipt_watchdog.py | 6dd308cf-ded3-47fe-bc59-9b44a3b45b22 |
| run_ha_watchdog_isolated.py | 70102990-8bf8-400d-87e2-7868591d2486 |
| ha_bridge_tick.py (fixture-only import trap) | 26f79447-626b-45b3-ac47-6a9bde179863 |

Manifest SHA256: 695d4f52ed10150d14f4fe29edabae3224462a40963f2dae386c488374894d59. On-device precheck and runner independently verified the manifest and all seven member hashes, directory/file permissions and membership. Original local ZIP SHA256 1d20df846f06c56a9c35b975b3377c2ef4d488f5709789a2b22c017766e62ffa, seven of seven hashed members verified. No production stub, token, journal or configuration transferred. Fixture uses synthetic data and loopback; Python-level safeguards are not kernel isolation.

## Physical acceptance results (actual HA SSH add-on)

- Fast suite job 53c18880-82a9-4cb8-990f-4a2fa53e62c8, timeout 30 s, done exit 0: MANIFEST_SHA256_PASS; ISOLATED_WATCHDOG_ACCEPTANCE_PASS 18/18; Ran 18 tests in 4.855s; OK. Covers exact receipt, real loopback lost ACK, retry limits, timeout/reaping, cooperative stop, unknown journal, invalid ACK, identity change, no ordinary tick in recovery cycle, and preflight/child budget.
- Default-timer job 0da5a848-3318-4897-8d46-d97d05b7c1f5, timeout 45 s, done exit 0: ISOLATED_FULL_BUDGET_PASS attempts=3 elapsed=43.018s outcome=RESULT_RETRY_EXHAUSTED journal=unchanged children=reaped. Exhaustion is the expected successful synthetic no-ACK outcome; not a claim that the real Worker acknowledged a simulated lost receipt. The full-budget command was run through the owner-authorized HA MCP with the permitted maximum of 45 s, despite earlier local-only recommendation; it completed successfully, but the margin was only 1.982 s and this is not a robust general procedure for slow systems. No retries of either task.
- Local regression repeated independently: 123/123 tests in 15.069 s, exit 0, ResourceWarning count 0. See live-ha-watchdog-regression.txt. The full regression is local, not 123 live tests on HA.

## Post-test production integrity

Read-only job b127615d-7e86-43b3-b91a-fa6899edc276, timeout 10 s, done exit 0: MONITOR_PROCESS RUNNING; STATUS RUNNING; DETAIL HA_AGENT_JOB_ACKNOWLEDGED; POLLS 74. PENDING_JOURNAL True was observed during this diagnostic's own execution; its result_received was later confirmed, not a stand-alone idle-journal measurement. All three test/diagnostic jobs have result_received audit entries under revision 4. Policy remains remote_enabled true, owner_admin_enabled true, scopes diagnostic/exec/read_file/write_file, revision 4.

Unchanged SHA256 from live baseline:

- ha_monitor.py: 5489d9ee6c9834a2178c5055563718ade173b042a6b2299352f6373f4b7144ef
- ha_bridge_tick.py: 563f52a675b560ca14b02a9fde19632959d61dad63eb0d001176991a6322f387
- ha_admin_agent_candidate.py: 8bd516fe03ba93d39c0176c465771b736ffdfb51516f9c0253d5e1221b370fc0
- recover_ha_queue_v2.py: d8709c60bf1c0f1bbebd7a69422be6fbc79dc0fcf707b8d98e71d881456450de

## Decision and remaining gates

ISOLATED HA PHYSICAL ACCEPTANCE PASS. Candidate not active. Production file hashes and permission revision preserved. Existing monitor was not stopped, restarted, or replaced. Test files remain in the private temporary fixture directory only; no cleanup or rollback was performed. No new service, keys or real backup archive created. Before separate production activation verify current deployed Worker same-result idempotency contract, startup wiring, baseline hashes, absence of pending/active/unknown jobs and descendants, and obtain owner-approved maintenance window; use only reviewed runtime candidate files, never fixture stub. Follow prior rollback runbook. Do not equate fixture acceptance with deployed Worker end-to-end lost-ACK acceptance. Full physical Backup DR acceptance remains blocked by the earlier rejected Keenetic package write and final local inventory/key escrow. No workaround attempted.
