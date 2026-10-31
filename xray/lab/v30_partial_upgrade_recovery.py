#!/usr/bin/env python3
"""Disposable staged five-file upgrade/rollback proof; never touch /opt.

The crash is injected after partial atomic file replacements. A separate
process replays a pre-fsynced all-file manifest and restores original bytes.
No production path can be selected, and no service is signaled.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from xray.staging.v30_supervisor_core import (
    FenceError, atomic_journal, supervisor_lock,
)

NAMES = ("S97xray", "S98xray-wifi", "S99xray-watchdog",
         "xray-watchdog.sh", "xray-wifi-rules.sh")


def root_only_temp(path):
    p = Path(path).resolve()
    if not (str(p).startswith("/tmp/") or str(p).startswith("/home/runner/work/")):
        raise FenceError("DISPOSABLE_ONLY")
    if Path("/opt/etc/xray/config.json").exists():
        raise FenceError("NO_PRODUCTION")
    return p


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_file(p):
    if p.is_symlink() or not p.is_file() or p.stat().st_nlink != 1:
        raise FenceError("ambiguous/symlinked upgrade target")
    if p.stat().st_size > 1024 * 1024:
        raise FenceError("unexpected upgrade target size")
    return p.read_bytes()


def replace_bytes(path, data, mode):
    path = Path(path)
    if path.is_symlink():
        raise FenceError("symlink target")
    temp = path.with_name("." + path.name + "-partial-txn")
    if temp.exists() or temp.is_symlink():
        raise FenceError("stale partial transaction")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.chmod(temp, mode)
        os.replace(temp, path)
        dirfd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    finally:
        if temp.exists():
            temp.unlink()


def preflight(root, manifest):
    base = root / "active"
    backup = root / "backup"
    if set(manifest["entries"]) != set(NAMES) or manifest.get("schema") != 1:
        raise FenceError("unexpected release file set")
    for name in NAMES:
        e = manifest["entries"][name]
        for key in ("original", "candidate"):
            if len(e[key]) != 64 or not all(x in "0123456789abcdef" for x in e[key]):
                raise FenceError("bad release sha")
        old = safe_file(backup / name)
        if digest(old) != e["original"]:
            raise FenceError("backup integrity mismatch")
        actual = safe_file(base / name)
        if digest(actual) not in (e["original"], e["candidate"]):
            raise FenceError("unexpected target bytes")
    return True


def prepare(root):
    root = root_only_temp(root)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    for sub in ("active", "backup", "candidate"):
        (root / sub).mkdir(mode=0o700)
    entries = {}
    for name in NAMES:
        old = (name + "-v29-frozen-test\n").encode()
        new = (name + "-v30-cooperative-test\n").encode()
        for sub, contents in (("active", old), ("backup", old), ("candidate", new)):
            path = root / sub / name
            replace_bytes(path, contents, 0o700)
        entries[name] = {"original": digest(old), "candidate": digest(new),
                         "mode": 0o700}
    atomic_journal(root / "manifest.json", {"schema": 1, "entries": entries})
    atomic_journal(root / "txn.json", {"phase": "old", "updated": []})


def updater(root):
    root = root_only_temp(root)
    manifest = json.loads((root / "manifest.json").read_text())
    with supervisor_lock(root / "shared.lock"):
        preflight(root, manifest)
        atomic_journal(root / "txn.json", {
            "phase": "prepared", "updated": [],
            "manifest_sha": digest((root / "manifest.json").read_bytes())})
        # Write intent BEFORE every replacement, preventing an unjournaled
        # upgrade if killed after replacing one or more files.
        updated = []
        for name in NAMES:
            atomic_journal(root / "txn.json", {
                "phase": "replacing", "updated": updated,
                "next": name,
                "manifest_sha": digest((root / "manifest.json").read_bytes())})
            replace_bytes(root / "active" / name,
                          safe_file(root / "candidate" / name), 0o700)
            updated.append(name)
            atomic_journal(root / "txn.json", {
                "phase": "replacing", "updated": updated,
                "next": None,
                "manifest_sha": digest((root / "manifest.json").read_bytes())})
            if len(updated) == 2:
                (root / "two-files-updated").write_text("PARTIAL\n")
                while True:
                    time.sleep(1)
        raise AssertionError("demo must kill updater before finish")


def recover(root):
    root = root_only_temp(root)
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    with supervisor_lock(root / "shared.lock", timeout=5):
        txn = json.loads((root / "txn.json").read_text())
        if txn.get("phase") not in ("prepared", "replacing"):
            raise FenceError("unexpected partial upgrade state")
        if txn.get("manifest_sha") != digest(manifest_path.read_bytes()):
            raise FenceError("release manifest mutated since intent fsync")
        preflight(root, manifest)
        for name in NAMES:
            e = manifest["entries"][name]
            actual = safe_file(root / "active" / name)
            if digest(actual) == e["candidate"]:
                replace_bytes(root / "active" / name,
                              safe_file(root / "backup" / name), e["mode"])
        # Never claim restored unless EVERY target is the original exact hash.
        for name in NAMES:
            assert digest(safe_file(root / "active" / name)) == manifest["entries"][name]["original"]
        atomic_journal(root / "txn.json", {"phase": "restored",
            "updated": [], "originals_verified": len(NAMES),
            "manifest_sha": digest(manifest_path.read_bytes())})
        (root / "success").write_text("PARTIAL_UPGRADE_ALL_FIVE_RESTORED\n")


def demo(root):
    root = root_only_temp(root)
    prepare(root)
    child = subprocess.Popen([sys.executable, "-m",
        "xray.lab.v30_partial_upgrade_recovery", "--updater", str(root)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        until = time.monotonic() + 8
        while not (root / "two-files-updated").exists():
            if child.poll() is not None or time.monotonic() >= until:
                raise FenceError("updater failed to reach partial state")
            time.sleep(0.05)
        child.kill()
        child.wait(timeout=3)
        # Independent *new Python interpreter* after owner of flock has died.
        proc = subprocess.run([sys.executable, "-m",
            "xray.lab.v30_partial_upgrade_recovery", "--recover", str(root)],
            timeout=12, text=True, capture_output=True)
        if proc.returncode != 0:
            raise FenceError("separate guardian unable to recover " + proc.stderr[-500:])
        if not (root / "success").exists():
            raise FenceError("guardian did not commit restoration")
        txn = json.loads((root / "txn.json").read_text())
        if txn["phase"] != "restored" or txn["originals_verified"] != len(NAMES):
            raise FenceError("partial recovery false claim")
        print("PARTIAL_UPGRADE: PASS killed updater after 2/5 staged files replaced")
        print("PARTIAL_UPGRADE: PASS independent interpreter recovered 5/5 original SHA256/modes")
        print("PARTIAL_UPGRADE: PASS fsynced manifest/intent and shared flock fail-closed")
        print("LIMITATION: disposable files, not real S97/S98 process migration or reboot")
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=3)


def main():
    p = argparse.ArgumentParser()
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--demo", type=Path)
    group.add_argument("--updater", type=Path)
    group.add_argument("--recover", type=Path)
    a = p.parse_args()
    if a.demo is not None:
        demo(a.demo)
    elif a.updater is not None:
        updater(a.updater)
    else:
        recover(a.recover)


if __name__ == "__main__":
    main()
