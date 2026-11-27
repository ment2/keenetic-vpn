"""Candidate adapter. Never invokes the VPN updater main or writes live Xray files.

Uses only the audited local subscription reader and parser. Raw subscription
and outbound settings remain local and are never published or printed.
"""
import argparse
import hashlib
import os
import runpy
import stat
import sys
from pathlib import Path
from monitoring.dynamic_snapshot import atomic_cache, MAX_NODES
from monitoring.vpn_inventory import inventory

# Explicit deployment path, distinct from all live Xray configurations.
DEFAULT_OUTPUT = "/opt/var/lib/vpn-monitor/full-subscription.json"
SOURCE_NAMES = ("xray-update-v23.py", "setup_xray.py",
                "xray_server_check.py", "xray_openai_probe.py")


def verify_sources(base, expected):
    base = Path(base)
    if set(expected) != set(SOURCE_NAMES):
        raise ValueError("all source digests required")
    for name in SOURCE_NAMES:
        p = base / name
        st = p.lstat()
        if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o022:
            raise ValueError("unsafe source file")
        if hashlib.sha256(p.read_bytes()).hexdigest() != expected[name]:
            raise ValueError("source digest mismatch")


def build_config(lines, converter):
    if not isinstance(lines, list) or not 1 <= len(lines) <= MAX_NODES:
        raise ValueError("unsupported subscription size")
    # Reject the complete generation on any parse/identity failure, rather than
    # quietly publishing a truncated subscription as current.
    outbounds = []
    for i, line in enumerate(lines, 1):
        outbound, _ = converter(line, i)
        if outbound.get("tag") != "vpn%02d" % i or outbound.get("protocol") != "vless":
            raise ValueError("unexpected outbound")
        outbounds.append(outbound)
    config = {"outbounds": outbounds}
    if len(inventory(config)) != len(lines):
        raise ValueError("inventory mismatch")
    return config


def refresh(*, base, expected, output=DEFAULT_OUTPUT):
    if Path(output) != Path(DEFAULT_OUTPUT):
        raise ValueError("only dedicated monitor snapshot path allowed")
    p = Path(output)
    parent = p.parent
    st = parent.lstat()
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o077:
        raise ValueError("private snapshot directory required")
    if p.is_symlink() or (p.exists() and not p.is_file()):
        raise ValueError("unsafe snapshot path")
    verify_sources(base, expected)
    # Isolated invocation, with known module origin and no updater main.
    base = str(Path(base).resolve())
    sys.path.insert(0, base)
    try:
        if any(name in sys.modules for name in ("setup_xray", "xray_server_check", "xray_openai_probe")):
            raise ValueError("unexpected preloaded source module")
        module = runpy.run_path(str(Path(base) / SOURCE_NAMES[0]), run_name="__vpn_monitor_subscription__")
        config = build_config(module["subscription"](), module["create_outbound"])
        verify_sources(base, expected)
        atomic_cache(p, config)
    finally:
        sys.path.remove(base)
    return len(config["outbounds"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-sha", action="append", required=True, metavar="NAME=SHA256")
    a = parser.parse_args()
    try:
        pairs = [s.split("=", 1) for s in a.source_sha]
        expected = dict(pairs)
        if len(pairs) != len(expected):
            raise ValueError("duplicate source digest")
        count = refresh(base="/opt/bin", expected=expected)
        print("SUBSCRIPTION_SNAPSHOT", count)
    except Exception as exc:
        # Never include exception text: parser errors can contain credentials.
        print("SUBSCRIPTION_SNAPSHOT_FAILED", type(exc).__name__)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
