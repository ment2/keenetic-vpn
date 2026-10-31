#!/usr/bin/env python3
"""Real MIPS32LE Xray with 8+8 guardian generation-CAS after owned parent death.

STRICTLY DISPOSABLE. The two guardian cohorts are real separate Python
processes. The actual Xray 26.2.6 MIPSLE child is owned by the single
parent worker and only this direct parent may send it signals. Guardian
processes never signal any historical Xray PID; they just atomically
claim/reconcile exact journal generations.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from xray.lab.v30_mips_guardian_failover import strict_lab, check, alive
from xray.lab.xray_v30_api_continuity import EchoBackend,free_port
from xray.lab.xray_v30_dual_process import UdpEcho, config
from xray.lab.v30_kernel49_cooperative_lab import (
    start_process,wait,wait_receipts,load,port_absent,real_xray_processes,
)
from xray.lab.v30_guardian_generation_race import (
    launch,await_file,all_losers,
)
from xray.staging.v30_kernel49_cooperative_ledger import Ledger
from xray.staging.v30_supervisor_core import FenceError,atomic_journal

def demo(root,xray,claimants=8):
    root=strict_lab(root)
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    binary=os.environ.get("XRAY_MIPS_BINARY","")
    import shutil
    qemu=shutil.which("qemu-mipsel")
    if not qemu or not binary or not Path(binary).is_file():
        raise FenceError("requires actual pinned MIPS binary and QEMU")
    version=subprocess.run([xray,"version"],capture_output=True,text=True,
                            check=True,timeout=18).stdout
    if "26.2.6" not in version or "linux/mipsle" not in version:
        raise FenceError("wrong Xray ISA/version")
    backend=EchoBackend("MIPS")
    udp=UdpEcho()
    backend.start();udp.start()
    old=None
    restored=None
    claim_procs=[]
    takeover_procs=[]
    port=free_port()
    try:
        (root/"candidate.json").write_text(json.dumps(config(
            port,backend.port,udp_port=udp.port,enable_udp=True)))
        atomic_journal(root/"runtime.json",{
            "qemu":qemu,"binary":str(Path(binary).resolve()),"port":port})
        raw=(root/"candidate.json").read_bytes()
        atomic_journal(root/"rescue-evidence.json",{
            "sha256":hashlib.sha256(raw).hexdigest(),
            "physical_independence_verified":False})
        ledger=Ledger(root)
        old=start_process(root,"owner",("--inject",))
        wait(root,"owner-ready",owner=old)
        started=ledger.submit("S97","START")
        receipts=wait_receipts(ledger,1,seconds=32)
        if receipts[-1]["sequence"]!=started["sequence"] or not check(port,"candidate"):
            raise FenceError("MIPS Xray TCP/UDP baseline failed")
        (root/"inject-crash").write_text("CRASH_AT_RESTART\n")
        req=ledger.submit("S97","RESTART")
        wait(root,"crash-window",owner=old,timeout=32)
        old_ident=load(root/"owner-identity.json")
        old.kill()
        old.wait(timeout=5)
        limit=time.monotonic()+14
        while not port_absent(port) or real_xray_processes(root):
            if time.monotonic()>limit:
                raise FenceError("old child/descendants or TCP listener still live")
            time.sleep(.04)
        if alive(old_ident["pid"],old_ident["start_ticks"]):
            raise FenceError("owner PID still alive")
        print("MIPS_CAS: PASS parent SIGKILL removed actual MIPSLE Xray child and listener",flush=True)
        # Two independent pools of 8 guardian processes race for same
        # original owner-generation. They operate under shared flock.
        atomic_journal(root/"original-owner.json",ledger.read()["owner"])
        claim_procs=launch(root,"claim",claimants)
        await_file(root/"claim-winner.json",timeout=12)
        deadline=time.monotonic()+13
        while not all_losers(root,"claim",claimants):
            if time.monotonic()>deadline:
                raise FenceError("first guardian cohort did not settle")
            time.sleep(.025)
        first=load(root/"claim-winner.json")
        winner=[p for p in claim_procs if p.pid==first["guardian_pid"]]
        if len(winner)!=1:raise FenceError("guardian winner identity mismatch")
        winner[0].kill()
        winner[0].wait(timeout=4)
        # Other contenders cannot steal claim without CAS.
        takeover_procs=launch(root,"takeover",claimants)
        await_file(root/"takeover-winner.json",timeout=12)
        deadline=time.monotonic()+13
        while not all_losers(root,"takeover",claimants):
            if time.monotonic()>deadline:
                raise FenceError("takeover guardians did not settle")
            time.sleep(.025)
        second=load(root/"takeover-winner.json")
        if second["token"]==first["token"] or second["attempt"]!=2:
            raise FenceError("recovery token/generation did not change")
        if not port_absent(port) or real_xray_processes(root):
            raise FenceError("unexpected live Xray while guardian attempts recovery")
        (root/"finish-guardian").write_text("VERIFIED_PROCESS_ABSENCE_LAB_ONLY\n")
        await_file(root/"reconciled",timeout=10)
        rows=ledger.read()["receipts"]
        if not any(r["sequence"]==req["sequence"] and r["status"]=="UNCERTAIN"
                   for r in rows):
            raise FenceError("interrupted MIPS restart was not UNCERTAIN")
        if sum(r["sequence"]==req["sequence"] for r in rows)!=1:
            raise FenceError("UNCERTAIN receipt duplicated")
        previous_generation=second["owner_generation"]
        restored=start_process(root,"owner")
        deadline=time.monotonic()+8
        while ledger.read()["owner"] is None:
            if restored.poll() is not None or time.monotonic()>deadline:
                raise FenceError("new sole-parent owner not started")
            time.sleep(.04)
        fresh=ledger.read()["owner"]
        if fresh["generation"]!=previous_generation+1:
            raise FenceError("fresh parent used stale generation")
        newreq=ledger.submit("S97","START")
        deadline=time.monotonic()+28
        while time.monotonic()<deadline:
            receipts=ledger.read()["receipts"]
            if any(r["sequence"]==newreq["sequence"] and r["status"]=="DONE"
                   for r in receipts):
                break
            time.sleep(.04)
        else:
            raise FenceError("new parent did not start MIPS Xray")
        if not check(port,"candidate"):
            raise FenceError("restored MIPS32LE Xray TCP+UDP failed")
        print("MIPS_CAS: PASS competing 8+8 guardians, one CAS claim per generation",flush=True)
        print("MIPS_CAS: PASS old RESTART UNCERTAIN exactly once; never auto-replayed",flush=True)
        print("MIPS_CAS: PASS new parent restored real MIPS32LE Xray SOCKS5 TCP+UDP",flush=True)
        print("LIMITATION: QEMU user-mode and LAB proof flags; not Keenetic 4.9 kernel cgroup or boot",flush=True)
    finally:
        for p in [old,restored,*claim_procs,*takeover_procs]:
            if p is not None:
                if p.poll() is None:p.kill()
                p.wait(timeout=5)
        backend.close();udp.close()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--demo",type=Path,required=True)
    p.add_argument("--xray",required=True)
    a=p.parse_args()
    demo(a.demo,a.xray)

if __name__=="__main__":main()
