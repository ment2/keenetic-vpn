#!/usr/bin/env python3
"""Deterministic NON-BOOTABLE RC6 offline rescue review package.

Includes pinned five archived scripts, a POSIX-sh rehearsal program,
SHA256SUMS, and explicit hardware NO-GO metadata. It is NOT an Entware
image, not an installed real boot hook, and contains no router secrets.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile
import io

from xray.lab.v30_review_rescue_bundle import file_set,fixed_tar,SOURCES

ROOT=Path(__file__).resolve().parents[2]
SHELL=Path(__file__).with_name("v30_rc6_rescue_guardian.sh")
NAME="v30-rc6-host-shell-rescue-NO-DEPLOY.tar"

def sha(s):return hashlib.sha256(s).hexdigest()

def entries():
    old=file_set()
    items={name:value for name,value in old.items() if name.startswith("originals/")}
    assert len(items)==5
    code=SHELL.read_bytes()
    if b"/opt/etc/" in code or b"killall xray" in code:
        raise ValueError("attempted unsafe executable")
    items["guardian.sh"]=code
    sha_lines=[sha(items[n])+"  "+n for n in sorted(items) if n.startswith("originals/")]
    items["SHA256SUMS"]=("\n".join(sha_lines)+"\n").encode()
    meta={
        "schema":1,"release":"v30-rc6-host-shell-rehearsal-only",
        "status":"NOT_BOOTABLE_NO_PRODUCTION_RESTORE",
        "originals_sha256":{n:sha(items[n]) for n in sorted(items)
                            if n.startswith("originals/")},
        "guardian_sha256":sha(code),
        "guardian_invocation":"host /bin/sh guardian.sh <review-source> <disposable-target>",
        "guardian_requires":"sha256sum,cmp,cp,mv,chmod,POSIX shell on runner",
        "guardian_executable_on_keenetic_verified":False,
        "guardian_usable_at_router_boot_without_entware":False,
        "mounted_on_distinct_physical_device":False,
        "physical_cold_boot_test_passed":False,
        "filesystem_powerloss_atomicity_proven":False,
        "production_authorized":False,
        "router_commands":[],
    }
    items["package-metadata.json"]=(json.dumps(meta,sort_keys=True,indent=2)+"\n").encode()
    return items

def verify(path):
    raw=Path(path).read_bytes()
    with tarfile.open(fileobj=io.BytesIO(raw),mode="r:") as tar:
        rows={}
        for item in tar.getmembers():
            if (not item.isfile() or item.name.startswith("/") or
                ".." in item.name.split("/") or item.name in rows or
                item.mode!=0o600 or item.issym() or item.islnk()):
                raise ValueError("unsafe tar member")
            rows[item.name]=tar.extractfile(item).read()
    if rows!=entries() or set(rows)!=set(entries()):
        raise ValueError("unverified or corrupted rescue package")
    meta=json.loads(rows["package-metadata.json"])
    if meta["production_authorized"] is not False:
        raise ValueError("untrusted authority")
    return {
        "status":"VERIFIED_OFFLINE_REHEARSAL_PACKAGE_ONLY",
        "sha256":sha(raw),"originals":5,
        "bootable":False,"production_authorized":False,
    }

def main():
    p=argparse.ArgumentParser()
    v=p.add_mutually_exclusive_group(required=True)
    v.add_argument("--build")
    v.add_argument("--verify")
    a=p.parse_args()
    if a.build:
        out=Path(a.build).resolve()
        if not str(out).startswith(("/tmp/","/home/runner/work/")) or out.exists() or out.is_symlink():
            p.error("disposable new file only")
        out.write_bytes(fixed_tar(entries()))
        out.chmod(0o600)
        print(json.dumps(verify(out),sort_keys=True))
    else:
        print(json.dumps(verify(a.verify),sort_keys=True))

if __name__=="__main__":main()
