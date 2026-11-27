# Home Assistant Network Recovery RC1 — physical acceptance
Date: 2026-11-27. Scope: Home Assistant Control (chat) only. No Cloudflare MCP, Keenetic Mobile, or other MCP invoked. No blocked Keenetic transfer retried. No production monitor stopped, startup hook changed, credentials rotated, queue reset, or journal deleted.

## Baseline and archive
Archive: /Home Assistant/2026-11-27-ha-network-rc1.zip; 12/12 manifest entries verified locally. Prior offline acceptance 39/39; not repeated locally. Original diagnostic 8a2b63e8-cddf-481c-862f-8ac61aac4be4 DONE exit 0. Target live status/hash job ff1e29c4-d9c7-4f1a-9154-2ed0bd90e5bb DONE exit 0: MONITOR_PROCESS RUNNING, HA_AGENT_IDLE, POLLS 22, Python 3.14.10, /usr/bin/openssl, root-owned agent directory 0700. Pending journal visible inside this job is expected for its own execution, not evidence of an unresolved receipt. All 5 installed source hashes matched reviewed baseline:

| File | SHA-256 |
|---|---|
| ha_bridge_tick.py | 563f52a675b560ca14b02a9fde19632959d61dad63eb0d001176991a6322f387 |
| ha_monitor_watchdog_candidate.py | 22ba0f5d070d21b38dd47cadc2b35316fe39d81cd1ab2ea46adb00489bf12b08 |
| ha_monitor_receipt_candidate.py | 9fdb271b3c53596bfe8a56898cd6070ce98a8bf622343f2bf5f676c9799dd02a |
| ha_receipt_retry.py | fa36a9fa719d8b157b4e663651e0c31269454361f50845998950bd3cf9f3a949 |
| ha_receipt_watchdog.py | 6618fe19220c841673292d6871bd380e2344489e642f93366de63b4a03daa57d |

## Isolated target staging
Directory /tmp/ha-network-rc1-20261127 (root-owned 0700). Create/copy unchanged four helpers: b420df66-9c91-41c8-90c3-017b7c4a8c43 DONE 0. Five normal HA MCP text writes (all DONE 0 FILE_WRITE_SHA256_VERIFIED):

| File | Job |
|---|---|
| ha_claim_connect_guard.py | 7d792f37-54fa-4718-a6db-401c3b166366 |
| prepare_candidate.py | 31255125-dd63-4b50-b5c2-95e4212e1e87 |
| test_network_candidate.py | 4946fc10-48bc-466a-9ec8-355187678681 |
| test_network_loopback.py | 5e3e6f42-b8d6-48a7-b1c8-32b9e3173cc2 |
| test_ha_receipt_watchdog.py | bd693d7d-4889-4618-bec7-96948a2e7b00 |

No duplicate submissions, no secret or journal copied. Staged membership, regular files, owner, link count, private modes and nine exact hashes verified by physical test job. Generator used exact on-device source bytes, checked source hashes/anchors and compiled both outputs. No reconstruction of redacted MCP source. Generated monitor matched archive hash. Candidate runtime file identities:

| File | SHA-256 |
|---|---|
| ha_claim_connect_guard.py | e991ff81201f6f5677ba74057fef78d0891c712684163252220e4ec9bc375ea6 |
| ha_bridge_tick_network_candidate.py | ae47c3ca22d7f4c1005ad3bb8fff4766b5035a08fb4de8faaf73ffcde6da2835 |
| ha_monitor_network_candidate.py | bc8535bc691edd7017355ef8494a8e1abbb9a08b1e6a5855c49b27def8fabcb3 |

## Physical test acceptance
Job 8238640e-2768-4c36-9b17-7d823fed694c, timeout 40s, DONE exit 0. STAGE_PRIVATE_FILES_PASS 9; nine source hashes OK; generated monitor hash OK. `python3 -B -m unittest -v test_network_candidate test_network_loopback test_ha_receipt_watchdog` (test-only proxy environment cleared, loopback and mocks; no external traffic from fixture intended). 39/39 PASS, 7.408 s: 16 transport/monitor/generator tests, 5 real loopback TLS tests, 18 watchdog regressions. Real lost claim response received exactly once by local test server; refusal before send classified; TLS rejection and HTTP rejection fail closed. Receipt lost ACK test redelivers identical receipt without command execution. Actual generated bridge compiled but was not run against production or imported/exercised by the isolated test suite; guard/monitor tests exercise reviewed modules, not end-to-end live claim protocol. Audit confirmed queued 12:27:46.256Z, claimed 12:27:53.697Z, result_received 12:28:03.715Z (revision 4). Final permission status remote_enabled=true, owner_admin_enabled=true, scopes diagnostic/exec/read_file/write_file, revision 4 unchanged. No deliberate live network outage. Exact historical URLError phase/reason remains unproven.

## Switch readiness and rollback (prepared, not executed)
1. Keep /tmp staging separate; it is ephemeral. Before maintenance, verify exact three candidate hashes above and five baseline hashes again, correct regular-file ownership and modes, and original startup entry. Copy only three new candidate filenames into /data/ha-admin-agent with owner-local, no-clobber installation and verification; never replace the five working baseline files. Preserve all original startup options. Do not copy tokens or journals. If staged files vanished, regenerate from exact reviewed baseline and package, not from redacted output. Stage never starts the real candidate.
2. Switch only from independent authorized owner-local HA SSH add-on terminal, not via a queued command whose receipt depends on that monitor. Coordinate exclusive maintenance, stop submitting new jobs, verify authoritative queue state/no in-flight or unknown jobs, verify local journal absence while idle (not from own queued command). The last 100 audit events alone are not authoritative proof of an empty queue. Existing owner-local recovery tooling is read-only unless explicitly invoked with mutation flags; do not reset or reconcile for routine switching. Stop if evidence is incomplete, pending journal exists, or unknown claim present. Never delete or overwrite journal.
3. Cooperatively stop current `python3 /data/ha-admin-agent/ha_monitor_watchdog_candidate.py stop` in independent terminal. Wait for old process and tick child to finish; verify both locks free and pending journal absent. Do not force kill in-flight child. Revalidate queue state and candidate integrity. Start the new monitor once: `python3 /data/ha-admin-agent/ha_monitor_network_candidate.py start`. Check status via same candidate's `status` and confirm correct process identity and advancing poll count. The inherited status is lock-based and does not alone identify which monitor owns lock. Keep existing boot hook unchanged for this trial; avoid add-on restart during trial.
4. From chat, after local switch, inspect existing jobs first, then submit exactly one new diagnostic and poll its returned ID only; confirm actual claim and receipt. Confirm stable RUNNING and poll progression. Safe DEGRADED and return to normal were tested in isolated fixture; do not induce production outage. If trial accepted, update only existing monitor startup entry in SSH add-on through authorized UI/maintenance, from old watchdog path to new network candidate path, preserving other options. Verify startup and eventual controlled reboot only after separate clean maintenance gate. No production autostart change yet.
5. Rollback: from independent local terminal, coordinate queue/idle, stop candidate cooperatively, wait for both locks and child, require no unresolved job/journal, restore original startup entry if changed, start unchanged old watchdog (`python3 /data/ha-admin-agent/ha_monitor_watchdog_candidate.py start`). If any unresolved operation/journal exists, preserve it and use established receipt-only/manual-review process before switch or rollback. Never auto-reconcile, reexecute, delete pending.json, reset queue or rotate credentials. Keep original files and candidate files available. Do not start both monitors or rely on status alone to establish identity.

Decision: PHYSICAL ISOLATED ACCEPTANCE PASS. Ready to prepare owner-local controlled activation, subject to fresh safety checks and exact installed bytes. Production activation and boot persistence remain pending. No claim that every URLError is recoverable: ambiguous post-send loss still deliberately blocks. No other MCP or public GitHub change. This RC is separate from OAuth RC6.
