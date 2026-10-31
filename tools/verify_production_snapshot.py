#!/usr/bin/env python3
"""Offline byte-integrity verification of the frozen nonsecret Xray source snapshot.

This verifies Git working tree content against a 2026-10-30 manifest, NOT
current router state, installed packages, credentials or staging behavior.
It cannot contact a router and must not attempt deployment.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


ROW = re.compile(r"^([0-9a-f]{64})  (opt/(?:bin|etc/init\\.d)/[^\\r\\n]+)  (100644|100755)$")
FORBIDDEN_NAMES = {
    "subscription.url", "config.json", "config.pending.json",
    "config.lastgood.json", "credentials.json", "secrets.json",
}
FORBIDDEN_EXTENSIONS = {".key", ".pem", ".p12", ".pfx", ".session", ".sqlite"}


def verify(root, *, check_modes=True):
    root = Path(root).resolve()
    manifest = root / "MANIFEST.sha256"
    if not manifest.is_file():
        raise ValueError("missing manifest")
    entries = {}
    for n, raw in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        if not raw or raw.startswith("#"):
            continue
        match = ROW.fullmatch(raw)
        if not match:
            raise ValueError(f"invalid manifest line {n}")
        digest, rel, mode = match.groups()
        if rel in entries:
            raise ValueError("duplicate path in manifest: " + rel)
        entries[rel] = (digest, mode)
    if len(entries) != 63:
        raise ValueError(f"unexpected manifest count: {len(entries)} (expected frozen 63)")
    actual = set()
    for p in root.rglob("*"):
        if p.is_symlink():
            raise ValueError("symlink not allowed: " + str(p.relative_to(root)))
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if rel in {"README.md", "MANIFEST.sha256"}:
            continue
        actual.add(rel)
        if p.name.lower() in FORBIDDEN_NAMES or p.suffix.lower() in FORBIDDEN_EXTENSIONS:
            raise ValueError("secret-bearing runtime path forbidden: " + rel)
        if rel not in entries:
            raise ValueError("unmanifested file in frozen snapshot: " + rel)
        observed_hash = hashlib.sha256(p.read_bytes()).hexdigest()
        if observed_hash != entries[rel][0]:
            raise ValueError("SHA256 mismatch: " + rel)
    missing = set(entries) - actual
    if missing:
        raise ValueError("missing manifest files: " + ", ".join(sorted(missing)))
    if check_modes:
        # Git modes are not router filesystem permissions.
        cp = subprocess.run(["git", "ls-files", "--stage", "--", "xray/production/opt"],
                            text=True, capture_output=True, check=True)
        git_modes = {}
        for line in cp.stdout.splitlines():
            match = re.match(r"^(100644|100755) [0-9a-f]{40,64} \\d+\\t(.+)$", line)
            if not match:
                raise ValueError("unexpected git ls-files --stage output")
            mode, repo_rel = match.groups()
            prefix = "xray/production/"
            if repo_rel.startswith(prefix):
                git_modes[repo_rel[len(prefix):]] = mode
        if set(git_modes) != actual:
            raise ValueError("tracked Git set differs from manifest snapshot")
        for rel, (_, expected_mode) in entries.items():
            if git_modes[rel] != expected_mode:
                raise ValueError("Git mode mismatch: " + rel)
    return {
        "status": "PASS_FROZEN_GITHUB_SNAPSHOT",
        "manifest_date": "2026-10-30",
        "verified_files": len(entries),
        "git_modes_checked": check_modes,
        "router_live_hashes_checked": False,
        "full_router_recovery_verified": False,
        "secrets_in_git_history_checked": False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default="xray/production")
    p.add_argument("--no-git-modes", action="store_true")
    p.add_argument("--output", help="write local JSON report; never a router path")
    args = p.parse_args()
    try:
        result = verify(args.root, check_modes=not args.no_git_modes)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print("FAIL: " + str(exc), file=sys.stderr)
        return 1
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
