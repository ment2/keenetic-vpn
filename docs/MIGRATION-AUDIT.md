# Library migration audit

Date: 2026-10-30. Source: `/Keenetic/Xray/`; destination: `ment2/keenetic-vpn`.

- Library inventory: **60 files** across `sources`, `patches`, `diagnostics`, and top-level documents.
- Imported with preserved filenames under `xray/`, except `xray-v27-v29-journal-2026-10-30.md`, which was initially committed to `docs/history/`.
- GitHub returned HTTP 422 `sha wasn't supplied` for several create-file calls: these indicate paths already existed; selected examples were subsequently fetched and confirmed.
- Full 60/60 content hash comparison: **not yet independently established**.
- Complete historical commit secret scan: **not yet independently established**.
- Complete Python compile, shell syntax, JSON validation: **not yet independently established**.
- Secret handling: the import used limited pattern-based masking (VLESS URLs and selected bearer/subscription strings); this is not a substitute for a comprehensive audit. `.gitignore` was added but cannot protect historical commits.
- No router production configuration, cron, firewall, routes or kill-switch was changed by the migration.

## Required final checks
1. Enumerate all 60 expected paths and fetch corresponding GitHub blobs.
2. Compare original and committed bytes or approved redacted equivalents; record SHA256 and explicit redaction diffs.
3. Validate all `.py` with `ast.parse`, shell scripts with `sh -n`, and JSON with `json.loads`.
4. Scan all Git commits for secrets (not just current tree); rotate any exposed live credentials and rewrite Git history only after explicit approval.
5. Document discrepancies and repair only the affected repository files.
