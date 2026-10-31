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

## Update 2026-10-31: frozen production snapshot and isolated CI

The outstanding gates above document the **initial 2026-10-30 Library archive migration**; later work supersedes their claims about missing CI and source comparison.

- A distinct `xray/production/` snapshot has 63/63 enumerated nonsecret production source/backup files copied and independently matched against live router SHA256 **as of 2026-10-30**, plus Git executable mode metadata. See `xray/production/README.md` and `xray/production/MANIFEST.sha256`.
- `tools/verify_production_snapshot.py` now enforces GitHub checkout SHA256, exact 63-file manifest coverage and Git executable mode parity; **it does not compare to the currently running router**. Selected production shell syntax and Python source AST checks run in GitHub CI.
- Source contracts and isolated model tests total **131/131 passing** in `Xray snapshot offline source contracts`, run **41189579857**.
- MIPS32LE QEMU staging laboratory runs real Xray 26.2.6 and supports SOCKS5 TCP/UDP and API continuity, but not the router kernel or real production cutover. `Xray v30 isolated MIPS32LE compatibility` run **41136161172 SUCCESS**.
- Full historic Git credential scanning, a faithful restore environment, current live hash refresh and the 2026-10-31 MenttwoGPT memory-sync patch parity are **still not complete**. Refer to `docs/production/2026-10-31-github-snapshot-staging-gap.md`.

Do not interpret the 60 historical Library files as 60 production source files, or 63 frozen source files as a complete router image.
