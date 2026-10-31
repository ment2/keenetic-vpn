#!/usr/bin/env python3
"""Disposable out-of-USB rescue *simulation* with real archived script bytes.

Two independent private directory trees; NO claim their test device differs
from USB /opt in hardware. A real production proof requires separate physical
mount/device and reboot checks, not just two pathnames.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from xray.lab.v30_partial_upgrade_recovery import (
    NAMES, prepare, safe_file, root_only_temp, digest, replace_bytes,
)
from xray.staging.v30_supervisor_core import (
    FenceError, atomic_journal, supervisor_lock,
)


def make_rescue(root):
    rescue = root / "rescue-outside-usb-simulated"
    rescue.mkdir(mode=0o700)
    manifest = json.loads((root / "manifest.json").read_text())
    for name in NAMES:
        data = safe_file(root / "backup" / name)
        if digest(data) != manifest["entries"][name]["original"]:
            raise FenceError("backup drift before off-USB rescue")
        replace_bytes(rescue / name, data, 0o700)
    atomic_journal(rescue / "rescue.json", {
        "schema":1, "source_kind":manifest["source_kind"],
        "original_sha256":{name:manifest["entries"][name]["original"] for name in NAMES},
        "release_manifest_sha256":digest((root / "manifest.json").read_bytes()),
        "separate_physical_mount_verified":False,
        "production_rescue_authorized":False,
    })
    fd=os.open(rescue,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)
    return rescue


def recover(root):
    root=root_only_temp(root)
    rescue=root / "rescue-outside-usb-simulated"
    if rescue.is_symlink() or not rescue.is_dir():
        raise FenceError("external independent rescue missing")
    manifest = json.loads((root / "manifest.json").read_text())
    meta=json.loads((rescue / "rescue.json").read_text())
    if meta.get("schema") != 1 or meta.get("production_rescue_authorized") is not False:
        raise FenceError("rescue schema or authority changed")
    if meta.get("release_manifest_sha256") != digest((root / "manifest.json").read_bytes()):
        raise FenceError("release manifest changed from rescue generation")
    if manifest.get("source_kind") != "frozen_actual_script_bytes":
        raise FenceError("not frozen real legacy source")
    # Strict preflight checks every rescue and active byte BEFORE ANY WRITES.
    for name in NAMES:
        entry=manifest["entries"][name]
        if meta.get("original_sha256",{}).get(name) != entry["original"]:
            raise FenceError("unexpected independent rescue digest")
        if digest(safe_file(rescue / name)) != entry["original"]:
            raise FenceError("corrupted out-of-usb rescue; zero writes")
        if digest(safe_file(root / "active" / name)) not in (
                entry["original"], entry["candidate"]):
            raise FenceError("unknown active script content; zero writes")
    with supervisor_lock(root / "shared.lock",timeout=3):
        txn=json.loads((root / "txn.json").read_text())
        if txn.get("phase") not in ("prepared","replacing"):
            raise FenceError("not a recoverable interrupted transaction")
        if txn.get("manifest_sha") != digest((root / "manifest.json").read_bytes()):
            raise FenceError("transaction intent drift")
        for name in NAMES:
            entry=manifest["entries"][name]
            data=safe_file(root / "active" / name)
            if digest(data) == entry["candidate"]:
                replace_bytes(root / "active" / name,
                              safe_file(rescue / name),entry["mode"])
        for name in NAMES:
            if digest(safe_file(root / "active" / name)) != (
                    manifest["entries"][name]["original"]):
                raise FenceError("failed independent restore verification")
        atomic_journal(root / "txn.json",{
            "phase":"restored","originals_verified":5,
            "rescue_source":"simulated_nonusb_tree",
            "physical_mount_verified":False,
        })
        print("OFFUSB_RESCUE: PASS independent fresh interpreter restored 5/5 original script bytes",flush=True)


def updater_crash(root):
    p=subprocess.Popen([sys.executable,"-m",
        "xray.lab.v30_partial_upgrade_recovery","--updater",str(root)],
        stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        deadline=time.monotonic()+8
        while not (root / "two-files-updated").exists():
            if p.poll() is not None or time.monotonic()>=deadline:
                raise FenceError("never reached 2/5 partial update")
            time.sleep(.05)
    finally:
        if p.poll() is None:
            p.kill()
        p.wait(timeout=3)


def invoke_recovery(root):
    return subprocess.run([sys.executable,"-m",
        "xray.lab.v30_nonusb_rescue_lab","--recover",str(root)],
        stdin=subprocess.DEVNULL,text=True,capture_output=True,timeout=15)


def demo(root):
    root=root_only_temp(root)
    prepare(root,real_bundle=True)
    rescue=make_rescue(root)
    manifest=json.loads((root / "manifest.json").read_text())
    updater_crash(root)
    usb_backup=root / "backup"
    usb_backup.rename(root / "usb-unplugged-test")
    before={n:digest(safe_file(root / "active" / n)) for n in NAMES}
    if not any(before[n] == manifest["entries"][n]["candidate"] for n in NAMES):
        raise FenceError("test did not actually replace files")
    original= (rescue / "S97xray").read_bytes()
    (rescue / "S97xray").write_bytes(b"corrupted-rescue-sentinel")
    corrupt=invoke_recovery(root)
    if corrupt.returncode==0:
        raise FenceError("corrupt independent rescue bypassed verification")
    after={n:digest(safe_file(root / "active" / n)) for n in NAMES}
    if before!=after:
        raise FenceError("failed rescue unexpectedly changed active scripts")
    print("OFFUSB_RESCUE: PASS corrupt independent rescue rejects before active writes",flush=True)
    replace_bytes(rescue / "S97xray",original,0o700)
    proc=invoke_recovery(root)
    if proc.returncode:
        raise FenceError("independent post-crash recovery blocked: "+proc.stderr[-500:])
    final={n:digest(safe_file(root / "active" / n)) for n in NAMES}
    expected={n:manifest["entries"][n]["original"] for n in NAMES}
    if final!=expected:
        raise FenceError("external rescue failed to restore five SHA256")
    state=json.loads((root/"txn.json").read_text())
    if state["phase"]!="restored" or state["originals_verified"]!=5:
        raise FenceError("false durable recovery journal")
    if (root/"backup").exists():
        raise FenceError("unexpectedly required disconnected USB backup")
    print("OFFUSB_RESCUE: PASS missing USB backup not used during independent restore",flush=True)
    print("OFFUSB_RESCUE: LIMITATION two paths on disposable runner, physical separate-mount/power-loss NOT PROVEN",flush=True)


def main():
    p=argparse.ArgumentParser()
    q=p.add_mutually_exclusive_group(required=True)
    q.add_argument("--demo",type=Path)
    q.add_argument("--recover",type=Path)
    a=p.parse_args()
    if a.demo:demo(a.demo)
    else:recover(a.recover)


if __name__=="__main__":
    main()
