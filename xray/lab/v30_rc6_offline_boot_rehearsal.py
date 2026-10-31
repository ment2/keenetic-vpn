#!/usr/bin/env python3
"""Offline RC6 USB-loss rescue rehearsal with host /bin/sh only.

The harness uses Python to *construct* disposable fixtures and inspect
results. Recovery itself executes through /bin/sh, sha256sum, cmp, cp, mv
with an empty environment except a minimal host PATH, no Python or Entware.
Both directories may reside on the SAME physical runner storage; this does
NOT prove physical separation, cold boot, durability, or kernel 4.9 safety.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from xray.lab.v30_review_rescue_bundle import file_set,SOURCES
from xray.staging.v30_supervisor_core import FenceError,atomic_journal

def sha(x):return hashlib.sha256(x).hexdigest()

def hash_active(dst):
    return {name:sha((dst/(name+".sh")).read_bytes()) for name in SOURCES}

def run_guard(guardian,src,target,fault=""):
    env={"PATH":"/usr/bin:/bin","HOME":"/nonexistent",
         "V30_RC6_FAULT":fault}
    return subprocess.run(["/bin/sh",str(guardian),str(src),str(target)],
                          env=env,capture_output=True,text=True,timeout=15)

def demo(root):
    root=Path(root).resolve()
    if not str(root).startswith(("/tmp/","/home/runner/work/")):
        raise FenceError("disposable runner only")
    root.mkdir(parents=True,mode=0o700,exist_ok=True)
    src=root/"review-nonusb-location-SIMULATED"
    active=root/"active"
    usb=root/"entware-usb-SIMULATED"
    src.mkdir(mode=0o700)
    (src/"originals").mkdir(mode=0o700)
    active.mkdir(mode=0o700)
    usb.mkdir(mode=0o700)
    inputs=file_set()
    sha_lines=[]
    expected={}
    for name in SOURCES:
        raw=inputs["originals/"+name+".sh"]
        target=src/"originals"/(name+".sh")
        target.write_bytes(raw)
        target.chmod(0o600)
        expected[name]=sha(raw)
        sha_lines.append(sha(raw)+"  originals/"+name+".sh")
        (active/(name+".sh")).write_bytes(b"RC6_CANDIDATE_NOT_AN_ORIGINAL_"+name.encode())
        (usb/(name+".sh")).write_bytes(raw)
    (src/"SHA256SUMS").write_text("\n".join(sha_lines)+"\n")
    # The recovery program is copied to the isolated simulated rescue
    # source. New shell invocations never read Python or checkout files.
    reviewed=Path(__file__).with_name("v30_rc6_rescue_guardian.sh").resolve()
    if not reviewed.is_file():
        raise FenceError("missing reviewed standalone shell guardian")
    guardian=src/"guardian.sh"
    guardian.write_bytes(reviewed.read_bytes())
    guardian.chmod(0o600)
    valid=run_guard(guardian,src,active,"after-2")
    if valid.returncode!=75:
        raise FenceError("fault injection failed: "+valid.stderr[-500:])
    intermediate=hash_active(active)
    replaced=sum(intermediate[name]==expected[name] for name in SOURCES)
    if replaced!=2:
        raise FenceError("after-2 really replaced "+str(replaced)+" not 2 files")
    print("RC6_RESCUE: PASS interrupted after exactly 2/5 original script copies",flush=True)
    # Simulated Entware USB is now disconnected. Recovery uses the *other*
    # directory and the host shell only.
    usb.rename(root/"entware-usb-disconnected-SIMULATED")
    # Even after a partial restore, a corrupt source MUST cause zero writes.
    invalid=src/"originals"/"S98.sh"
    pristine=invalid.read_bytes()
    invalid.write_bytes(pristine+b"\nMALICIOUS_SUFFIX\n")
    before=hash_active(active)
    failed=run_guard(guardian,src,active)
    if failed.returncode==0 or hash_active(active)!=before:
        raise FenceError("corrupt rescue source bypassed preflight or changed active files")
    invalid.write_bytes(pristine)
    print("RC6_RESCUE: PASS damaged original archive refused with zero further writes",flush=True)
    # A brand new shell process (no Python or Entware in its environment)
    # replays the operation and confirms all five original bytes.
    recovered=run_guard(guardian,src,active)
    if recovered.returncode!=0 or hash_active(active)!=expected:
        raise FenceError("fresh host shell did not restore all five: "+recovered.stderr[-700:])
    if (root/"entware-usb-SIMULATED").exists():
        raise FenceError("USB was not actually disconnected in fixture")
    record={
      "schema":1,"status":"HOST_SHELL_RECOVERY_ONLY",
      "restored_origins":5,"induced_partial_restore_count":2,
      "no_python_dependency_in_guardian":True,
      "entware_usb_simulated_disconnected":True,
      "physical_separate_device_verified":False,
      "cold_boot_keenetic_verified":False,
      "physical_powerloss_fsync_verified":False,
      "kernel49_exec_verified":False,
      "production_restore_authorized":False,
      "router_commands":[],
      "original_sha256":expected
    }
    atomic_journal(root/"rehearsal-result.json",record)
    print("RC6_RESCUE: PASS exact original 5/5 after USB simulation via fresh host /bin/sh",flush=True)
    print("RC6_RESCUE: HARD_NO_GO same runner storage, shell runtime and physical boot unverified",flush=True)
    return record

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--demo",type=Path,required=True)
    a=p.parse_args()
    demo(a.demo)

if __name__=="__main__":main()
