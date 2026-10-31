#!/usr/bin/env python3
"""Build/verify reproducible, NON-EXECUTABLE Xray v30 review-only rescue tar.

Contains only five exact archived original shell scripts and a pinned hash
index + no-deploy metadata. All tar member permissions are 0600; source
production modes 0755 are recorded but NEVER applied. No restore /opt,
no live network or kernel actions, no dependency on Entware at build time.

This is an archive kept on GitHub Actions runner, NOT an external USB-free
boot volume. Physical mount/boot/rescue gates remain false.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile

from xray.lab.v30_release_manifest_contract import ROOT, verify as verify_release

ARCHIVE = "v30-kernel49-rescue-review.tar"
SOURCES = ("S97","S98","S99","watchdog","wifi_rules")
METADATA = "rescue-metadata.json"
FIXED_MTIME = 0

def sha(data):
    return hashlib.sha256(data).hexdigest()

def fixed_tar(entries):
    out=io.BytesIO()
    with tarfile.open(fileobj=out,mode="w",format=tarfile.USTAR_FORMAT) as t:
        for path,data in sorted(entries.items()):
            info=tarfile.TarInfo(path)
            info.size=len(data)
            info.mtime=FIXED_MTIME
            info.mode=0o600
            info.uid=info.gid=0
            info.uname=info.gname=""
            t.addfile(info,io.BytesIO(data))
    return out.getvalue()

def file_set():
    if verify_release()["verified"]!=9:
        raise ValueError("RC1 pins invalid")
    release=json.loads((ROOT/"xray/staging/v30-release-manifest-v1.json").read_text())
    entries={}
    pinned={}
    for item in release["entries"]:
        if item["role"] not in SOURCES:
            continue
        raw=(ROOT/item["legacy_snapshot_path"]).read_bytes()
        if sha(raw)!=item["legacy_snapshot_sha256"]:
            raise ValueError("frozen source mismatch")
        name="originals/"+item["role"]+".sh"
        entries[name]=raw
        pinned[name]={"sha256":sha(raw),"recorded_original_mode":"0755",
                      "archive_mode":"0600", "source":item["legacy_snapshot_path"]}
    if len(entries)!=5 or set(pinned)!={"originals/"+x+".sh" for x in SOURCES}:
        raise ValueError("incomplete original archive")
    meta={
        "schema":1,"release":"v30-kernel49-review-rescue-v1",
        "status":"OFFLINE_REVIEW_ONLY_NOT_BOOTABLE",
        "authorizes_production_restore":False,
        "contains_executable_recovery_agent":False,
        "stored_outside_entware_usb_on_real_keenetic":False,
        "tested_after_physical_power_loss":False,
        "tested_without_physical_usb":False,
        "actual_mount_identity_verified":False,
        "requires":"separate owner-approved physical boot/USB-free rescue",
        "files":pinned,"allowed_actions":["read","hash_verify"],"router_commands":[],
    }
    entries[METADATA]=(json.dumps(meta,sort_keys=True,indent=2)+"\n").encode()
    return entries

def inspect(archive):
    blob=Path(archive).read_bytes()
    with tarfile.open(fileobj=io.BytesIO(blob),mode="r:") as t:
        members=t.getmembers()
        if len(members)!=6:
            raise ValueError("incorrect tar member count")
        rows={}
        for m in members:
            if not m.isfile() or m.issym() or m.islnk() or m.mode!=0o600:
                raise ValueError("executable or unsafe tar member")
            if m.name.startswith("/") or ".." in m.name.split("/") or m.name in rows:
                raise ValueError("archive traversal/duplicate")
            stream=t.extractfile(m)
            if stream is None:
                raise ValueError("unreadable tar member")
            rows[m.name]=stream.read()
    expected=file_set()
    if rows!=expected:
        raise ValueError("archive content corrupted or repacked")
    meta=json.loads(rows[METADATA])
    if meta["authorizes_production_restore"] is not False:
        raise ValueError("unsound release authority")
    return {"status":"PASS_REVIEW_ONLY_ARCHIVE","sha256":sha(blob),
            "originals":5,"production_authorized":False,
            "physical_rescue_proven":False}

def output_path(p):
    p=Path(p).resolve()
    if not (str(p).startswith("/tmp/") or str(p).startswith("/home/runner/work/")):
        raise ValueError("only disposable runner output path allowed")
    return p

def main():
    p=argparse.ArgumentParser()
    m=p.add_mutually_exclusive_group(required=True)
    m.add_argument("--build")
    m.add_argument("--verify")
    a=p.parse_args()
    if a.build:
        out=output_path(a.build)
        out.parent.mkdir(parents=True,exist_ok=True)
        if out.is_symlink() or out.exists():
            raise ValueError("refuse existing or symlink target")
        out.write_bytes(fixed_tar(file_set()))
        out.chmod(0o600)
        print(json.dumps(inspect(out),sort_keys=True))
    else:
        print(json.dumps(inspect(a.verify),sort_keys=True))

if __name__=="__main__":main()
