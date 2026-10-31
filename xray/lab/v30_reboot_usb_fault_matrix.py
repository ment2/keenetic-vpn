#!/usr/bin/env python3
"""Disposable v30 crash/reboot-replay/USB-missing backup fault matrix.

Uses the ACTUAL frozen five legacy source bytes and actual staged replacements
in private runner dirs. Fake reboot is full process restart with persistent
journal, NOT a kernel reboot or physical Keenetic USB-loss proof.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from xray.lab.v30_partial_upgrade_recovery import (
    NAMES, prepare, recover, safe_file, root_only_temp, digest,
)
from xray.staging.v30_supervisor_core import FenceError


def snapshot(root):
    return {name: digest(safe_file(root / "active" / name)) for name in NAMES}


def spawn_updater_and_crash(root):
    child = subprocess.Popen([sys.executable, "-m",
        "xray.lab.v30_partial_upgrade_recovery", "--updater", str(root)],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)
    try:
        end = time.monotonic() + 9
        while not (root / "two-files-updated").exists():
            if child.poll() is not None or time.monotonic() > end:
                raise FenceError("partial updater did not reach 2/5")
            time.sleep(0.04)
        child.kill()
        child.wait(timeout=3)
        return snapshot(root)
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=3)


def fresh_replay(root):
    return subprocess.run([sys.executable, "-m",
        "xray.lab.v30_partial_upgrade_recovery", "--recover", str(root)],
        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=12)


def run(root):
    root = root_only_temp(root)
    prepare(root, real_bundle=True)
    initial = snapshot(root)
    changed = spawn_updater_and_crash(root)
    if initial == changed:
        raise FenceError("fault injection did not replace any scripts")
    original_manifest = json.loads((root / "manifest.json").read_text())
    if original_manifest["source_kind"] != "frozen_actual_script_bytes":
        raise FenceError("not actual source fixture")
    # Model the Entware backup storage vanishing WITHOUT touching /opt.
    backup = root / "backup"
    unplugged = root / "usb-offline"
    backup.rename(unplugged)
    before_failed_recovery = snapshot(root)
    denied = fresh_replay(root)
    if denied.returncode == 0:
        raise FenceError("USB-missing recovery unsafely claimed success")
    if snapshot(root) != before_failed_recovery:
        raise FenceError("USB-missing recovery changed active scripts")
    if (root / "success").exists():
        raise FenceError("USB-missing recovery wrongly wrote success receipt")
    print("USB_FAULT: PASS missing backup blocks before any additional active script writes", flush=True)
    # Simulate operator reconnecting the same *byte-identical* private backup.
    unplugged.rename(backup)
    restarted = fresh_replay(root)
    if restarted.returncode != 0:
        raise FenceError("fresh process after simulated reboot could not recover: " +
                         restarted.stderr[-500:])
    final = snapshot(root)
    if final != initial:
        raise FenceError("fresh recovery did not restore all five original hashes")
    txn = json.loads((root / "txn.json").read_text())
    if txn["phase"] != "restored" or txn["originals_verified"] != 5:
        raise FenceError("journal restoration not durable")
    print("REBOOT_REPLAY: PASS new interpreter replays fsynced 2/5 update journal", flush=True)
    print("REBOOT_REPLAY: PASS restored 5/5 archived S97/S98/S99/watchdog/rules SHA256", flush=True)
    print("LIMITATION: process restart simulation; not real router reboot or USB physical recovery", flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--demo", type=Path, required=True)
    args = p.parse_args()
    run(args.demo)


if __name__ == "__main__":
    main()
