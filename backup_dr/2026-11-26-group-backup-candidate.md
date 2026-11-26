# Backup DR: group candidate, 2026-11-26
Base commit 3b38f26bc7ba2df85f9cfa5e07d83c562a0ff781.

## Live evidence
HA queue policy revision 4, both old jobs failed before execution, admin scopes preserved. Receiver job 663bf294-1fff-45c9-a0ba-9e4224a08add done, exit 0: LISTENER_RC 0, PID 1655. Router job 8c954c7d-3443-4502-be36-90bc09b4c479 done, exit 0: KEENETIC_HTTP_RECEIPT_PASS. HA job 1c19bc83-25df-432a-9e9a-bbcd40751cf7 done, exit 0: HA_SSD_FIXTURE_RESTORE_PASS; digest 7b9437eb3f183fefddd16584917cad1120d6ac2703ab6fd718104d94b85e25f3. This was the original synthetic byte fixture, NOT a live production archive or v3.1 manifest/SQLite acceptance. Recovery script read-only AUTH_OK REVISION 4; pending journal true inside its own job is expected.

## Inventory (aggregate only)
Router job 8960bdc0-fc0f-4e54-b53d-63969d0b3a1d done exit 0. Telegram AI: 22 py / 131797 bytes; 948 other / 769649 bytes; 2 logs / 13974478 bytes; 2 session / 2048000 bytes; 28 JSON / 23940 bytes. Excluded tests, caches, profile_backups and .git from scan. Xray: 17 JSON / 120007 bytes; 13 other / 86522 bytes; 1 sh / 649 bytes. init.d 19 regular files / 17807 bytes; cron spool 1 / 2362 bytes. No file contents, keys or session data exported. Not a complete inventory of Entware, router configuration, HA integration or external agent files. Actual per-file allowlist remains to be reviewed; no automatic collection of all 'other' files.

## Offline candidate
Stable group IDs, explicit allowlists, independent derived keys and scheduler state, per-group quotas with aggregate configured cap 2 GiB and SSD reserve 5 GiB, 4 MiB source budget, conservative WAL size estimate, authenticated route /v1/backup/<group> on the same receiver port. Reject wrong membership even if ciphertext authenticates. Test independent scheduler and SQLite restore. Retention callable per group but not scheduled. Removed groups retain archives; configured quota sum does not account for their existing storage, so production needs global quota accounting and migration rules. No streaming for >4 MiB individual files. No persistent service/cron enabled. Production key generation/distribution and separate recovery escrow still pending. No real secrets uploaded.

## Current live blocker
HA v3.1 fixture write job 4d3a785f-b37a-4fe3-aaf9-3b30cce9becd submitted; corresponding Keenetic write was blocked by tool safety systems. Do not retry via alternative tools or circumvent the block. The v3.1 manifest/SQLite LAN fixture was not started. Preserve original live PASS, continue offline or owner-managed authorized installation. No production config changed.
