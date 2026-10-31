# Keenetic VPN / Xray

Private archive of Keenetic Ultra KN-1810 VPN/Xray development, laboratory experiments, diagnostics and historical source snapshots.

## Layout
- `xray/sources/`: historical Python, shell, init and watchdog sources. `.readback`, `LEGACY`, and `DRAFT` names are deliberately retained.
- `xray/patches/`: offline fixtures and draft patches; **not** production configurations.
- `xray/diagnostics/`: audit and test reports.
- `xray/*.md`: design and migration history.
- `docs/history/`: v27–v29 journal snapshot.
- `docs/integration/`: interface with Keenetic Mobile.

## Safety
No automatic deployment. Never commit actual subscription URLs, VLESS credentials, API tokens, production `config.json`, or router secrets. `.gitignore` is only preventive and does not remove committed history. Do not execute historical migration scripts blindly. Test Python syntax, shell syntax and Xray configuration in an isolated lab before deployment.

## Related repository
Keenetic Mobile Cloudflare Worker and router agent: [ment2/keenetic-control](https://github.com/ment2/keenetic-control). Keep agent/Worker sources there; this repository covers VPN/Xray artifacts and interface documentation.

## Provenance
Source snapshots originate from ChatGPT Library `/Keenetic/Xray/`, with paths mirrored under `xray/` except the v27–v29 journal archived at `docs/history/`. Migration audit is recorded in `docs/MIGRATION-AUDIT.md`.

## Current verified status (2026-10-31)

- **Frozen 2026-10-30 nonsecret Xray source snapshot:** 63/63 enumerated files and backups with historical live-router SHA256 parity. This is **not** a complete router clone or a current 2026-10-31 parity check.
- **GitHub CI snapshot integrity:** all 63 committed file bytes and tracked Git executable modes are checked against `xray/production/MANIFEST.sha256`; selected shell syntax, Python AST, limited current-tree secret checks and 131 unit/contract tests pass in CI.
- **Executable isolated laboratory exists:** Xray 26.2.6 MIPS32LE under QEMU, including two real Xray processes, SOCKS5 TCP and UDP ASSOCIATE, candidate failure, old-process recovery and API `bo/ado/rmo` tests. **This is not a KeeneticOS-faithful staging router**; actual TPROXY, kernel fail-closed, shared ingress, installed watchdog and disaster-recovery bootstrapping remain unverified.
- **Related memory-sync incident:** MenttwoGPT Cloudflare delivery depends on local SOCKS5. The 2026-10-31 production patch belongs to `ment2/menttwogpt` and is not part of the frozen 63-file Xray snapshot.

See [current snapshot/staging gap matrix](docs/production/2026-10-31-github-snapshot-staging-gap.md), [production incident dependency](docs/incidents/2026-10-31-menttwogpt-memory-delivery-dependency.md), and [controlled first-cutover plan](docs/production/2026-10-31-controlled-first-api-migration-v30-plan.md).

**Offline repository check:** `python tools/verify_production_snapshot.py`. This command compares a GitHub checkout to the frozen manifest, **not** to a live router. Do not deploy or merge this branch without explicit approval.
