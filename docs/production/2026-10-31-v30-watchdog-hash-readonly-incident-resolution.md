# Keenetic Xray v30: read-only watchdog SHA incident resolution

Date: 2026-10-31. Scope restricted to repository `ment2/keenetic-vpn`, branch `feature/xray-v30-stable-tcp-ingress-lab-20261031`.

**Decision: WATCHDOG PRODUCTION FILE HAS NOT DRIFTED. THE PINNED `WD_SHA` LITERAL IN THE CANARY SOURCE IS MALFORMED (63 vs 64 hex characters).** The previously filed report `docs/production/2026-10-31-v30-canary-install-plan-failed-watchdog-drift.md` accurately records a preflight refusal, but its hypothesis that the live script changed is **disproved**. Do not change the live watchdog in response.

## User-approved bounds and actions

Owner authorized **only read-only** diagnostics of `/opt/bin/xray-watchdog.sh` versus root-only backup `/opt/var/backups/xray-v30-precutover-20261031-1045Z/opt/bin/xray-watchdog.sh`, no file content/secrets printed and documentation in GitHub/Library. **No --plan retry, no source patch on router, no --trial/--rollback/--guardian, no Xray/watchdog/S98 signals, no firewall/routes/cron/Cloudflare/production config change, no merge/deploy.**

Single router job `fdf51310-f08e-488e-b2a4-fd510ec13081`, **done, exit_code=0**. Inspection timestamp **2026-10-31 12:07:34.862946 UTC**. Executed read-only Python `lstat`, SHA256, manifest metadata and byte-level difflib comparison, outputting no raw file contents or secrets.

## Verified on-router file evidence

| Field | Live `/opt/bin/xray-watchdog.sh` | Saved backup copy |
|---|---|---|
| Type | regular, not symlink | regular, not symlink |
| UID:GID | `0:0` | `0:0` |
| File mode | `0755` | `0600` (backup protection, expected) |
| Size | `649 bytes` | `649 bytes` |
| Lines | 28 | 28 |
| SHA256 | `dddfcc1d324e30b91df041378645ada869a18b4d35f2842383e5d319fc859e08` | `dddfcc1d324e30b91df041378645ada869a18b4d35f2842383e5d319fc859e08` |
| mtime UTC | `2026-10-25T17:29:33.343999+00:00` | same (copied metadata) |
| ctime UTC | `2026-10-25T17:29:33.351999+00:00` | `2026-10-31T10:45:27.407943+00:00` (created backup copy) |

Manifest `manifest.json` has **exactly one** matching entry, recording the same 64-digit watchdog SHA256. Manifest SHA256 itself `f27c336f66f1bbb9ef22a82f7e8aa84f80f9bee808b3a87abf6a5372e79d5c62` agrees with baseline. Backup entry verified.

File comparison: `BYTE_EQUAL=True`, size delta 0, `DIFFERENCE_HUNKS_COUNT=0`. There is **no observable byte drift** from the backed-up source. Differences in permissions and ctime arise from copying the backup with mode 0600, not source content changes. File mtime/ctime alone do not prove there were no edits and reversions before the observation; the defensible finding is byte identity with the 2026-10-31 backup.

## Root cause confirmed against GitHub source

Source `xray/staging/v30_first_cutover_canary.py` at immutable Git blob SHA `08b172af082df1284be35f39592942c0942a377b` (the approved installed version), read from exact feature branch, contains:

```python
WD_SHA = "dddcc1d324e30b91df041378645ada869a18b4d35f2842383e5d319fc859e08"
```

That quoted SHA is **63 hex characters**, whereas correct live, backup and manifest value is the 64-character:

```text
dddfcc1d324e30b91df041378645ada869a18b4d35f2842383e5d319fc859e08
```

The source literal lacks the **fourth character `f`**. Therefore `verify_backup()` compares a real, valid 64-hex SHA to an impossible 63-hex literal and unconditionally raises `GateError: supervisor/source drift detected: xray-watchdog.sh` under this verified configuration.

Previous GitHub CI `41198879628` passed 240/240 offline tests plus **source file** SHA256 and import, but tests did **not** validate every embedded pinned expected hash against an authentic live/backup manifest and did not reject a 63-character constant. Green CI is not validation of this router preflight.

## Immediate safety / permitted next steps

1. **STOP**: Do not run `--plan` again; its refusal is explained and installing the same file again is pointless.
2. Leave the installed canary source at `/opt/bin/v30_first_cutover_canary.py` as is, root-only `0700`, SHA256 `93f187cadbe985e65e67f619f9f3d7c1c8f120cdb9a506b22419a75cdeabdb4d`, until separately approved to replace it. Do not change the watchdog.
3. With **future separate scope approval**, prepare corrected candidate **only in this feature branch**: replace the single WD_SHA literal with the fully verified 64-hex value. Add tests that assert all pinned SHA strings are exactly 64 lowercase hex and compare live backups/manifest against immutable fixtures. Revalidate GitHub CI and compute a **new exact source blob SHA and SHA256**.
4. Present **full corrected source / exact absolute path / new checksum** for a new installation-only approval; never silently patch the on-router file or assume prior approval covers changed bytes.
5. After approved reinstall, new read-only `--plan` may be evaluated **only under separate authorization**. No cutover/rollback without a further distinct explicit approval and real fail-closed tests.

**Outcome:** diagnostic completed read-only; the apparent watchdog drift is an erroneous canary constant, **not evidence of a modified production watchdog**. No changes to live router, Cloudflare, route/firewall/cron, production configuration or GitHub main/snapshot.
