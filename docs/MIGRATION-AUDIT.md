# Library migration audit

Date: 2026-10-30. Source: `/Keenetic/Xray/`; destination: `ment2/keenetic-vpn`.

## Verified result
- **60 of 60 Library files fetched and compared against the GitHub default branch.**
- **60/60 exact text-content matches; 0 missing and 0 mismatched.**
- 59 files retain the Library relative path under `xray/`. The v27–v29 journal is under `docs/history/`.
- The comparison used complete content returned by the Library reader and GitHub file fetcher, not only filenames or commit counts.
- No masking differences were detected in the 60 committed snapshots. This does **not** prove that no secrets exist in those snapshots.
- GitHub commit search returned 64 commits at the time of the earlier inventory; this is not a historical secret audit.

## Source review findings
- `update_xray_subscription.py.readback-2026-10-30` invokes curl with connection/max-time limits, validates candidate Xray config, writes restricted-permission temporary files, and uses atomic replace with a last-good backup. Good defensive patterns, but review failure recovery, concurrent invocations and health checks before any production adoption.
- `xray_server_check.py.readback-2026-10-30` uses bounded subprocess timeouts and process cleanup; inspect port contention, temporary files, and probe false positives.
- `xray-watchdog-switch-v26.py` probes local SOCKS5; a listening port alone is insufficient proof of upstream VPN or Telegram/OpenAI connectivity.
- `xray-update-v23.1-2026-10-29.py` validates candidate config with Xray; its versioned source is historical and not verified as the current deployed updater.
- Multiple `LEGACY`, `DRAFT`, `readback` and v23–v29 variants coexist. This is an **archive**, not yet a single buildable/deployable release. Define an authoritative version and reproducible test pipeline before treating GitHub as the deploy source.

## Outstanding security and quality gates
1. **Full secret audit of all commit objects and the current tree remains unverified.** Do not claim secrets are absent. Run a dedicated Git history scanner from a trusted environment, then rotate any exposed active credentials. Rewriting history requires separate approval.
2. Python syntax, shell syntax and JSON syntax for all files have not yet been executed in a local test environment; runtime and integration tests are also outstanding.
3. CI pipeline, manifest/lockfile and release promotion controls are not yet established.
4. Avoid storing production `config.json`, subscription URLs, VLESS UUIDs, API keys, router passwords or private keys in Git. `.gitignore` does not retroactively scrub history.
5. No production router, Xray, cron, firewall, route or kill-switch change was made during this audit.

## Release readiness
**Archive integrity: PASS (60/60).**
**Production-ready GitHub release: NOT YET VERIFIED.**
