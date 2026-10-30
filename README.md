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
