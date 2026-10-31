#!/usr/bin/env python3
"""Disposable multi-process guardian CAS recovery stress for v30 Linux49.

N separate guardians race for the same crashed owner generation. Exactly
one claimant wins. It dies holding the generation claim; a second N-process
cohort races to take over the exact stale claim, and only one may commit.
Never signals any Xray PID; only orchestrator-owned disposable guardians.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from xray.staging.v30_supervisor_core import FenceError, atomic_journal, proc_stat
from xray.staging.v30_kernel49_cooperative_ledger import Ledger,disposable

PROOF={key:True for key in (
    "old_parent_exited","old_child_exited","all_descendants_drained",
    "old_listener_absent","rescue_sha_verified","no_unfenced_writers",
    "two_consecutive_sealed_scope_scans")}

def await_file(path, timeout=8):
    end=time.monotonic()+timeout
    while not path.exists():
        if time.monotonic()>end:
            raise FenceError("guardian coordination timed out")
        time.sleep(.025)

def contender(root,round_,number):
    root=disposable(root)
    await_file(root/("go-"+round_))
    ledger=Ledger(root)
    ticks=proc_stat(os.getpid())[2]
    try:
        if round_=="claim":
            owner=json.loads((root/"original-owner.json").read_text())
            result=ledger.begin_scoped_recovery(
                expected_generation=owner["generation"],guardian_ticks=ticks)
        else:
            old=json.loads((root/"claim-winner.json").read_text())
            result=ledger.takeover_scoped_recovery(
                old,guardian_ticks=ticks,verified_old_guardian_dead=True)
    except FenceError:
        atomic_journal(root/(round_+"-loser-"+str(number)+".json"),
                       {"outcome":"DENIED_STALE_OR_CONCURRENT"})
        return
    atomic_journal(root/(round_+"-winner.json"),result)
    if round_=="takeover":
        await_file(root/"finish-guardian")
        ledger.finish_scoped_recovery(result,PROOF)
        (root/"reconciled").write_text("ONE_GENERATION_RECOVERED\n")
        return
    while True:time.sleep(.2)

def launch(root,round_,n):
    procs=[]
    for k in range(n):
        log=(root/(round_+"-"+str(k)+".log")).open("w")
        p=subprocess.Popen([sys.executable,"-m",
            "xray.lab.v30_guardian_generation_race",
            "--contender",str(root),"--round",round_,"--index",str(k)],
            stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
            start_new_session=True)
        log.close()
        procs.append(p)
    (root/("go-"+round_)).write_text("GO\n")
    return procs

def all_losers(root,round_,n):
    return len(list(root.glob(round_+"-loser-*.json")))==n-1

def demo(root,n=8):
    root=disposable(root)
    root.mkdir(parents=True,mode=0o700,exist_ok=True)
    ledger=Ledger(root)
    req=ledger.submit("S97","RESTART")
    ledger.submit("cron","CHECK_HEALTH")
    owner=ledger.open_owner(fresh_known_absence=True)
    atomic_journal(root/"original-owner.json",owner)
    ledger.claim(owner)
    p1=[]
    p2=[]
    try:
        p1=launch(root,"claim",n)
        await_file(root/"claim-winner.json")
        end=time.monotonic()+12
        while not all_losers(root,"claim",n):
            if time.monotonic()>end:raise FenceError("first cohort did not settle")
            time.sleep(.02)
        first=json.loads((root/"claim-winner.json").read_text())
        matches=[p for p in p1 if p.pid==first["guardian_pid"]]
        if len(matches)!=1:raise FenceError("first claimant PID not unique")
        matches[0].kill()
        matches[0].wait(timeout=4)
        print("GENERATION_CAS: PASS first 8 guardians only one claimed; owner generation pinned",flush=True)
        p2=launch(root,"takeover",n)
        await_file(root/"takeover-winner.json")
        end=time.monotonic()+12
        while not all_losers(root,"takeover",n):
            if time.monotonic()>end:raise FenceError("takeover cohort did not settle")
            time.sleep(.02)
        next_=json.loads((root/"takeover-winner.json").read_text())
        if next_["token"]==first["token"] or next_["attempt"]!=2:
            raise FenceError("improper recovery claim CAS")
        (root/"finish-guardian").write_text("FINISH\n")
        await_file(root/"reconciled")
        rows=ledger.read()["receipts"]
        if [r["status"] for r in rows]!=["UNCERTAIN","CANCELLED_UNCERTAIN"]:
            raise FenceError("UNCERTAIN duplicated or old pending replayed")
        if ledger.read()["owner"] is not None or ledger.read()["blocked"]:
            raise FenceError("recovery did not clear stale owner")
        new=ledger.open_owner(fresh_known_absence=True)
        if new["generation"]!=owner["generation"]+1:
            raise FenceError("new owner generation not incremented exactly once")
        print("GENERATION_CAS: PASS after first guardian SIGKILL exactly one of 8 took over claim",flush=True)
        print("GENERATION_CAS: PASS UNCERTAIN recorded exactly once, stale queued cron cancelled",flush=True)
        print("GENERATION_CAS: PASS new parent generation excludes stale guardians",flush=True)
        print("LIMITATION: synthetic disappearance proof; physical process containment not verified",flush=True)
    finally:
        for p in [*p1,*p2]:
            if p.poll() is None:
                p.kill()
            p.wait(timeout=5)

def main():
    p=argparse.ArgumentParser()
    k=p.add_mutually_exclusive_group(required=True)
    k.add_argument("--demo",type=Path)
    k.add_argument("--contender",type=Path)
    p.add_argument("--round",choices=("claim","takeover"))
    p.add_argument("--index",type=int,default=0)
    a=p.parse_args()
    if a.demo:demo(a.demo)
    else:contender(a.contender,a.round,a.index)

if __name__=="__main__":main()
