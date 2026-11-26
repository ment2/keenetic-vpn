# Backup DR — HA receiver staging and watchdog observation

Baseline: ment2/keenetic-vpn commit 5297052a8ea71a8fddff3fd2c62781d4c2dd6826; frozen backup source commit 33f8091631885c70b4a1ac5e4648322d63cb1f46 (147 previous offline tests). No later local draft code used.

## Live watchdog and receiver prerequisites

HA MCP exec job e6889b74-700e-44a9-9a9d-5018a0c71269, timeout 10 s, completed exit 0. RUNNING, HA_AGENT_IDLE, POLLS 11 (previously 8); pending journal present during own diagnostic, not independent evidence of unresolved work. SHARE_FREE 104908226560 bytes; /share/keenetic-backup-dr absent; bind probe to 192.168.0.169:8765 succeeded and socket closed. No receiver listening or enabled. No deliberate duplicate-result submission or induced fault; version 54 repeat-result idempotency remains unattested.

## Inactive HA staging

Reconstructed 17-module service_v35 dependency closure from archived v3.5 source and verified envelope-generation overlay, not the later local draft. All 17 Git blob IDs independently matched frozen GitHub commit. Local reproducible ZIP `ha-receiver-staging-33f8091.zip` (23072 bytes), SHA256 `1dde45de9f75c236a0d85ba8609355a665d84b96dcd2fee63b632c5794c7bcdd`; internal SHA256 17/17 and ZIP integrity verified. `ha-receiver-staging-manifest-33f8091.json` SHA256 `aab58873371d8f16b3ecc58724bd586a7a297a27bf69e84333061d7b6ee096e0`. ZIP and manifest saved in Library.

Directory `/data/keenetic-backup-dr-staging-33f8091` created on HA with mode 0700, job f1021e71-b799-4caa-9a97-b58b52f86a14 done exit 0. All 17 modules submitted once through normal HA text write_file. Six writes individually confirmed done exit 0 FILE_WRITE_SHA256_VERIFIED; the other 11 were submitted/queued and not yet independently verified completed. See exact IDs and expected hashes in `ha-receiver-staging-jobs-33f8091.json`. Verification-only job 899695da-2d80-4940-9fa1-ab57639ce8c6 queued once behind writes; timeout 15 s, exact filename set, ownership/mode/link count/SHA256 checks, isolated import service_v35, no service startup. Poll existing jobs only. No replacements or automatic repeats.

## Activation limits

HA staging is not a running backup service. No real master key, plan, archive, secret, listener, autostart, retention run, router job or actual restore created by this stage. Existing HA watchdog and production configuration unchanged. Inventory remains candidate only: 38 paths across five nonempty groups; Telegram state and Entware config groups empty; local review of sensitive state and key escrow incomplete. Earlier Keenetic transfer restriction remains in force; no alternate transfer or reattempt to evade it. Frozen source also retains previously documented slow-HTTP/decompression and historical-retention limits. Do not equate this staged package with an approved production release. Next: poll existing write and verification IDs; if all pass, HA receiver staging is complete, but live activation and first real restore remain blocked on authorized sender installation, final plan and secure shared key/escrow. No additional feature development in this stage.
