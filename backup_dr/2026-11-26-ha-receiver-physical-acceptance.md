# Backup DR — HA receiver physical acceptance

Baseline documentation: ment2/keenetic-vpn commit 217251f24951a396aef79129af3a49681a923fb0. Frozen runtime source: 33f8091631885c70b4a1ac5e4648322d63cb1f46 (147/147 prior offline tests). No later draft used.

## Staging completion

Read the existing 17 write job IDs from the saved registry and polled each, with no resubmission. All 17 completed exit 0, FILE_WRITE_SHA256_VERIFIED. Verification job 899695da-2d80-4940-9fa1-ab57639ce8c6 completed exit 0: HA_RECEIVER_STAGE_SHA256_PASS 17; HA_RECEIVER_IMPORT_PASS. The original command checks exact filenames, regular single-link files, effective-user ownership, mode 0600, SHA-256, and imports service_v35 from /data/keenetic-backup-dr-staging-33f8091. Audit confirms result_received at 1795727448385, revision 4. Directory was previously created mode 0700. No repeated staging writes or verification job.

## Target physical synthetic acceptance

Fetched the existing test_acceptance_v35.py from frozen source; Git blob f466c4c70da1ed8483f8976fd0597d75f6640c23. One HA exec job 1c4688ad-1390-491f-8999-235d4b97bb1a, timeout 25 s, imported the verified installed runtime with Python -I -B and ResourceWarning promoted to error. TemporaryDirectory rooted in /share, synthetic key bytes(range(32)), synthetic text and SQLite WAL database; receiver listens only on 127.0.0.1 with dynamic port. No production service started or persistent files/configuration changed by test. No Keenetic call or real secret used. Test exercised encrypted durable upload, synthetic lost acknowledgment, receiver restart, identical ciphertext retry, one archive only, unchanged source no resend, digest filename verification, decrypted manifest restore, SQLite quick_check and row 42, original database remains readable. Actual output:

```text
test_lost_ack_restart_exact_ciphertext_sqlite_restore (__main__.Acceptance.test_lost_ack_restart_exact_ciphertext_sqlite_restore) ... ok

----------------------------------------------------------------------
Ran 1 test in 1.250s

OK
```

Completed exit 0; audit result_received 1795727485592 at revision 4. Current permission status unchanged: remote/admin enabled, scopes diagnostic/exec/read_file/write_file, revision 4. This verifies target runtime and actual HA loopback HTTP/SQLite recovery, not router-to-HA production backup or Worker result idempotency.

## Deployment decision and blockers

HA receiver runtime staged and physical synthetic acceptance PASS. No persistent receiver listener/autostart, operational key, final plan, or production backup/restore. Previously blocked Keenetic package transfer remains blocked; no retries, alternate transfer, or instructions to bypass. Prior inventory has 38 candidate paths; final local sensitive-state/Entware inventory and secure common master key/independent escrow remain open. No real backup source, token, or encryption key exposed. Frozen build retains documented slow HTTP/decompression limits and historical retention limitations. Do not mark production backup enabled. No additional feature development undertaken. Do not repeat this completed staging or synthetic test. Next action only when a permitted sender installation route and final local plan/key procedure are established; otherwise report the blocker.
