#!/usr/bin/env python3
"""Disposable Linux-4.9-compatible parent-owned MIPSLE Xray rehearsal.

Actual Xray 26.2.6 QEMU SOCKS5 TCP+UDP; NO kernel TPROXY or real VPN.
The controller is always Xray's own parent. A dead parent causes SIGKILL
via PR_SET_PDEATHSIG; recovery NEVER signals an orphan via a stale PID.
"""
import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from xray.lab.v30_parent_owned_kernel49 import (
    FenceError, spawn_owned, owned_signal, reap_owned,
)
from xray.lab.v30_mips_guardian_failover import strict_lab, check, wait_check, alive
from xray.lab.xray_v30_api_continuity import EchoBackend, free_port
from xray.lab.xray_v30_dual_process import UdpEcho, config
from xray.staging.v30_supervisor_core import atomic_journal, supervisor_lock


def read(path):
    return json.loads(Path(path).read_text())


def xray_args(root, generation):
    data=read(root/"runtime.json")
    return [data["qemu"],data["binary"],"run","-config",
            str(root/(generation+".json"))]


def worker(root, generation, case):
    root=strict_lab(root)
    runtime=read(root/"runtime.json")
    port=runtime["port"]
    journal=root/(generation+"-prepared.json")
    if generation=="restored":
        previous=read(root/"candidate-prepared.json")
        # The new guardian is NOT the previous Xray's parent. It MUST
        # NEVER os.kill(previous.pid), even if the journal seems plausible.
        deadline=time.monotonic()+12
        while alive(previous["pid"],previous["start_ticks"]):
            if time.monotonic()>deadline:
                raise FenceError("orphan candidate did not die; no unsafe signal")
            time.sleep(0.04)
        if check(port,"candidate"):
            raise FenceError("candidate still owns socket; cannot recover")
    with supervisor_lock(root/"shared.lock",timeout=3):
        args=xray_args(root,"candidate" if generation=="candidate" else "old")
        def prepared_callback(child):
            if case=="prepared":
                (root/"prepared-window").write_text("PARENT_JOURNALED_CHILD_BEFORE_EXEC\n")
                while True:
                    time.sleep(.1) # test driver kills parent; pipe EOF exits child
        child=spawn_owned(args[0],args,journal,on_prepared=prepared_callback)
        if not wait_check(port,generation if generation=="candidate" else "restored",20):
            raise FenceError("real MIPSLE Xray SOCKS5 TCP+UDP startup not healthy")
        atomic_journal(root/"transition.json",{
            "phase":generation+"_healthy","mode":"direct_parent_unreaped",
            "parent_pid":child.parent_pid,
            "child_pid":child.pid,"start_ticks":child.ticks,
            "no_pidfd":True,"no_guardian_signal":True})
        (root/(generation+"-ready")).write_text("REAL_MIPSLE_TCP_UDP_PASS\n")
    if generation=="restored":
        while True:time.sleep(.2)
    if case=="child_exit":
        while not (root/"inject-child-death").exists():
            time.sleep(.02)
        result=owned_signal(child,signal.SIGTERM)
        if result!="SENT_TO_DIRECT_CHILD_WITH_RESERVED_PID":
            raise FenceError("child death did not target owned child")
        reap_owned(child,timeout=10)
        atomic_journal(root/"transition.json",{"phase":"child_reaped",
                    "parent_owned":True,"pidfd_used":False})
        (root/"child-reaped").write_text("DIRECT_PARENT_REAP_COMPLETE\n")
    elif case=="rollback":
        while not (root/"request-rollback").exists():
            time.sleep(.02)
        with supervisor_lock(root/"shared.lock",timeout=3):
            atomic_journal(root/"transition.json",{"phase":"rollback_intent",
                 "parent_owned":True,"no_stale_pid_signal":True})
            result=owned_signal(child,signal.SIGTERM)
            if result not in ("SENT_TO_DIRECT_CHILD_WITH_RESERVED_PID",
                              "ALREADY_EXITED_UNREAPED"):
                raise FenceError("unexpected child owner")
            (root/"rollback-window").write_text("INTERRUPTED_ROLLBACK_AFTER_SIGNAL\n")
            while True:time.sleep(.1)
    else:
        while True:time.sleep(.2)


def spawn_worker(root, gen, case):
    log=(root/(gen+".log")).open("w")
    p=subprocess.Popen([sys.executable,"-m",
        "xray.lab.v30_parent_owned_mips_recovery",
        "--worker",str(root),"--generation",gen,"--case",case],
        stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
        start_new_session=True)
    log.close()
    return p


def wait_file(root,name,process,seconds):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        if (root/name).exists():
            return
        if process.poll() is not None:
            logpath=root/("restored.log" if name.startswith("restored") else "candidate.log")
            tail=logpath.read_text(errors="replace")[-2400:] if logpath.exists() else "(no log)"
            raise FenceError("owned worker died early: "+name+"; logs="+tail)
        time.sleep(.04)
    raise FenceError("owned worker timeout: "+name)


def demo(root,xray,case):
    root=strict_lab(root)
    root.mkdir(mode=0o700,parents=True,exist_ok=True)
    binary=os.environ.get("XRAY_MIPS_BINARY","")
    import shutil
    qemu=shutil.which("qemu-mipsel")
    if not qemu or not binary or not Path(binary).is_file():
        raise FenceError("missing qemu / pinned MIPS executable")
    version=subprocess.run([xray,"version"],capture_output=True,
                           text=True,check=True,timeout=20).stdout
    if "26.2.6" not in version or "linux/mipsle" not in version:
        raise FenceError("require real MIPSLE Xray 26.2.6")
    port=free_port()
    backend=EchoBackend("MIPS")
    udp=UdpEcho()
    backend.start()
    udp.start()
    p=None
    restored=None
    try:
        for name in ("old.json","candidate.json"):
            (root/name).write_text(json.dumps(config(port,backend.port,
                                    udp_port=udp.port,enable_udp=True)))
        atomic_journal(root/"runtime.json",{
            "qemu":qemu,"binary":str(Path(binary).resolve()),"port":port})
        p=spawn_worker(root,"candidate",case)
        if case=="prepared":
            wait_file(root,"prepared-window",p,10)
            prepared=read(root/"candidate-prepared.json")
            assert prepared["phase"]=="PREPARED_PARENT_OWNED"
        else:
            wait_file(root,"candidate-ready",p,25)
            prepared=read(root/"candidate-prepared.json")
            assert check(port,"candidate"),"candidate failed TCP+UDP after ready"
            if case=="child_exit":
                (root/"inject-child-death").write_text("OWNER_SIGNAL_ONLY\n")
                wait_file(root,"child-reaped",p,12)
                assert read(root/"transition.json")["phase"]=="child_reaped"
            elif case=="rollback":
                (root/"request-rollback").write_text("ROLLBACK\n")
                wait_file(root,"rollback-window",p,12)
                assert read(root/"transition.json")["phase"]=="rollback_intent"
        p.kill()
        p.wait(timeout=5)
        deadline=time.monotonic()+12
        while alive(prepared["pid"],prepared["start_ticks"]):
            if time.monotonic()>deadline:
                raise FenceError("PDEATHSIG failed; child survives parent")
            time.sleep(.05)
        print("PARENT49: PASS actual owned Xray child disappeared after owner death/exit",flush=True)
        # Fresh worker is sole parent of the restored Xray. It does NOT
        # signal stale PIDs from candidate's durable journal.
        restored=spawn_worker(root,"restored","normal")
        wait_file(root,"restored-ready",restored,28)
        if not check(port,"restored"):
            raise FenceError("restored MIPSLE Xray lacks TCP/UDP")
        state=read(root/"transition.json")
        if state["phase"]!="restored_healthy" or not state["no_pidfd"]:
            raise FenceError("restored transaction not complete")
        print("PARENT49: PASS real MIPS32LE QEMU Xray SOCKS5 TCP+UDP recovered",flush=True)
        print("PARENT49: PASS never signaled a stale PID; parent-owned WNOWAIT and PDEATHSIG",flush=True)
        print("PARENT49: PASS failure injection "+case,flush=True)
        print("LIMITATION: user-mode QEMU; not Keenetic 4.9 kernel TPROXY or physical boot",flush=True)
    finally:
        for w in (p,restored):
            if w and w.poll() is None:
                w.kill()
                w.wait(timeout=5)
        backend.close()
        udp.close()


def main():
    pa=argparse.ArgumentParser()
    m=pa.add_mutually_exclusive_group(required=True)
    m.add_argument("--demo",type=Path)
    m.add_argument("--worker",type=Path)
    pa.add_argument("--xray")
    pa.add_argument("--case",choices=("normal","parent_crash","child_exit","rollback","prepared"),
                    default="parent_crash")
    pa.add_argument("--generation",choices=("candidate","restored"))
    a=pa.parse_args()
    if a.demo:
        demo(a.demo,a.xray,a.case)
    else:
        if a.generation is None:
            pa.error("worker requires --generation")
        worker(a.worker,a.generation,a.case)


if __name__=="__main__":
    main()
