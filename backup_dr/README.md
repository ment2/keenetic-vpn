# Keenetic Backup & Disaster Recovery — HTTP candidate

Offline test run: 13/13 PASS in 2.071 s. Run `cd backup_dr && python3 -m unittest -v`.
Both Keenetic and HA passed the AES-256-GCM known-answer, roundtrip and tamper test on their actual libcrypto. No new packages required.
HTTP POST uses an explicit allowlisted source IP, encrypted payload, distinct derived encryption and receipt keys, authenticated receipt, and content-addressed durable storage. Retries of the identical ciphertext are idempotent while the archive exists. SQLite uses online backup and in-memory serialization. No plaintext archive is persisted.

**Not a production deployment.** Fixture-only live test is queued, with public synthetic key and nonsecret data, separate /share directory, no existing service changes.
Limits: 48 MiB uncompressed source budget, 64 MiB AEAD message limit; memory copies on MIPS need measuring. Snapshot is not globally transactional. Persistent scheduler, manifest, quota/retention, sender spooling and retry, bounded SQLite backup duration, inventory, independent key escrow and secure provisioning, HA monitoring and live isolated restore remain acceptance gates. Receiver authenticates ciphertext, not archive structure. No replay guarantee across retention expiry. Do not deploy as-is.
