#!/usr/bin/env python3
"""Fail on high-confidence embedded secrets in the frozen Xray source snapshot.

This lightweight current-tree scanner is NOT a Git-history scan and cannot
prove no secrets exist. Never print detected secret values.
"""
import argparse
from pathlib import Path
import re
import sys


RULES = (
    ("private_key_block", re.compile(r"-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("openai_token", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}\b")),
    ("vless_with_uuid", re.compile(
        r"vless://[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}@", re.I)),
    ("embedded_url_password", re.compile(r"https?://[A-Za-z0-9_.-]+:[^\s/'\"@]{8,}@[A-Za-z0-9_.-]+")),
)


def inspect_text(text):
    return [name for name, pattern in RULES if pattern.search(text)]


def scan(root):
    root = Path(root)
    count = 0
    findings = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        count += 1
        data = path.read_text(encoding="utf-8", errors="replace")
        for rule in inspect_text(data):
            # Only the relative path and detector name are reported.
            findings.append((path.relative_to(root).as_posix(), rule))
    return count, findings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="xray/production/opt")
    args = parser.parse_args()
    count, findings = scan(args.root)
    for rel, rule in findings:
        print(f"FAIL: {rel} matched {rule}", file=sys.stderr)
    if findings:
        return 1
    print(f"PASS: {count} snapshot files scanned for high-confidence embedded credentials")
    print("LIMIT: history, obfuscated secrets and external files NOT scanned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
