"""RC38 read-only verification of a private archived Xray rescue bundle.

Checks archival SHA256, size, symlink containment and manifest mode metadata.
Never writes or restores files, signals processes, changes routes or reads
network credentials outside the selected archive directory.
"""
import hashlib
import json
import os
from pathlib import Path


class RescueAuditError(ValueError):
    pass


def _mode(value):
    if not isinstance(value, str) or not value.startswith("0o"):
        raise RescueAuditError("invalid original_mode")
    try:
        result = int(value, 8)
    except ValueError as exc:
        raise RescueAuditError("invalid original_mode") from exc
    if not 0 <= result <= 0o777:
        raise RescueAuditError("invalid original_mode")
    return result


def audit_bundle(root):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise RescueAuditError("untrusted archive directory")
    manifest_path = root / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise RescueAuditError("untrusted manifest")
    manifest = json.loads(manifest_path.read_text())
    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries:
        raise RescueAuditError("empty archive manifest")
    seen = set()
    issues = []
    permission_restore_required = 0
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise RescueAuditError("invalid manifest entry")
        path = entry.get("path")
        if not isinstance(path, str) or not path.startswith("/opt/"):
            raise RescueAuditError("non-opt path")
        parts = Path(path).parts
        if any(part in (".", "..") for part in path.split("/")):
            raise RescueAuditError("traversal in manifest")
        rel = Path(path.lstrip("/"))
        if str(rel) in seen:
            raise RescueAuditError("duplicate manifest entry")
        seen.add(str(rel))
        item = root / rel
        # Forbid symlinks at any level beneath archive root. resolve() alone
        # would allow escapes and hide unexpected filesystem topologies.
        current = root
        for part in rel.parts:
            current = current / part
            if current.is_symlink():
                raise RescueAuditError("archive symlink encountered")
        if not item.is_file():
            issues.append("MISSING_ENTRY_" + str(i))
            continue
        sha = entry.get("sha256")
        expected_size = entry.get("size")
        if not isinstance(sha, str) or len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
            raise RescueAuditError("invalid sha256")
        if not isinstance(expected_size, int) or expected_size < 0 or expected_size > 100_000_000:
            raise RescueAuditError("invalid size")
        if item.stat().st_size != expected_size:
            issues.append("SIZE_MISMATCH_" + str(i))
            continue
        digest = hashlib.sha256(item.read_bytes()).hexdigest()
        if digest != sha:
            issues.append("HASH_MISMATCH_" + str(i))
        if (item.stat().st_mode & 0o777) != _mode(entry.get("original_mode")):
            permission_restore_required += 1
    return {
        "status": "ARCHIVE_VALID_READ_ONLY" if not issues else "ARCHIVE_INVALID",
        "entries": len(entries),
        "issues": sorted(issues),
        "permission_restore_required": permission_restore_required,
        "off_usb_rescue_proven": False,
        "physical_boot_recovery_proven": False,
        "production_authorized": False,
        "router_actions": [],
    }


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--archive", required=True)
    a = p.parse_args()
    print(json.dumps(audit_bundle(a.archive), sort_keys=True))


if __name__ == "__main__":
    main()
