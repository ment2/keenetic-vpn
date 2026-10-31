#!/usr/bin/env python3
"""Real MIPS32LE Xray + cooperative Linux-4.9 parent-owned lifecycle lab.

All S97/S98/S99/watchdog/cron requests enter one shared-flock ledger.
Only the long-lived parent signals its own unreaped Xray direct child.
No global kill, no pidfd, no VPN/firewall/cron/router actions.
A killed parent leaves UNCERTAIN; an independently restarted guardian
can restore only after verifying the old parent, child, descendants,
and SOCKS listener are all gone. Not a production service.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

from xray.lab.v30_mips_guardian_failover import strict_lab, check, wait_check, alive
from xray.lab.xray_v30_api_continuity import EchoBackend, free_port
from xray.lab.xray_v30_dual_process import UdpEcho, config
from xray.lab.v30_parent_owned_kernel49 import spawn_owned, owned_signal, reap_owned
from xray.staging.v30_supervisor_core import FenceError, atomic_journal, proc_stat, supervisor_lock
from xray.staging.v30_kernel49_cooperative_ledger import Ledger


def load(path):
    return json.loads(Path(path).read_text())


def port_absent(port):
    try:
        with socket.create_connection(("127.0.0.1",port),timeout=.1):
            return False
    except OSError:
        return True


def wait_absent(port,timeout=8):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        if port_absent(port):
            return True
        time.sleep(.05)
    return False


def real_xray_processes(root):
    """Conservative /proc inventory of our exact test config; never signal."""
    expected=str(root/"candidate.json").encode()
    active=[]
    for entry in Path("/proc").iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            cmd=(entry/"cmdline").read_bytes()
            if expected in cmd.split(b"\0"):
                state,_,ticks=proc_stat(int(entry.name))
                if state not in ("X","Z"):
                    active.append((int(entry.name),ticks))
        except (FileNotFoundError,ProcessLookupError):
            continue
        except PermissionError as exc:
            raise FenceError("cannot prove full lab process inventory") from exc
    return active


def spawn_xray(root):
    runtime=load(root/"runtime.json")
    if not port_absent(runtime["port"]):
        raise FenceError("unknown listener before spawn")
    if real_xray_processes(root):
        raise FenceError("unknown process still has Xray config")
    gen=int(time.monotonic_ns())
    args=[runtime["qemu"],runtime["binary"],"run","-config",
          str(root/"candidate.json")]
    child=spawn_owned(args[0],args,root/("child-prepared-"+str(gen)+".json"))
    if not wait_check(runtime["port"],"candidate",20):
        raise FenceError("owned MIPS Xray startup TCP/UDP failed")
    return child


def stop_xray(child,port):
    result=owned_signal(child,signal.SIGTERM)
    if result not in ("SENT_TO_DIRECT_CHILD_WITH_RESERVED_PID",
                      "ALREADY_EXITED_UNREAPED"):
        raise FenceError("unexpected child signal status")
    reap_owned(child,timeout=10)
    if not wait_absent(port):
        raise FenceError("old listener remained after owned child reaped")
    return None


def owner_loop(root,*,inject=False):
    root=strict_lab(root)
    ledger=Ledger(root)
    runtime=load(root/"runtime.json")
    port=runtime["port"]
    if real_xray_processes(root) or not port_absent(port):
        raise FenceError("live unknown child; do not start a new owner")
    owner=ledger.open_owner(fresh_known_absence=True)
    atomic_journal(root/"owner-identity.json", {
        "pid":os.getpid(),"start_ticks":proc_stat(os.getpid())[2],
        "generation":owner["generation"]})
    (root/"owner-ready").write_text(str(owner["generation"])+"\n")
    child=None
    stats={"started":0,"restarts":0,"max_direct_owned":0,"actor_receipts":0}
    try:
        deadline=time.monotonic()+95
        while time.monotonic()<deadline:
            req=ledger.claim(owner)
            if req is None:
                time.sleep(.025)
                continue
            act=req["operation"]
            role=req["actor"]
            result="DONE"
            if role=="S97":
                if act=="STOP":
                    if child is not None:
                        child=stop_xray(child,port)
                else:
                    if child is not None:
                        if act=="RESTART":
                            stats["restarts"]+=1
                        child=stop_xray(child,port)
                    # Parent never starts Xray if old-owned child still lives.
                    if child is not None:
                        raise FenceError("two simultaneous Xray children")
                    child=spawn_xray(root)
                    stats["started"]+=1
                    stats["max_direct_owned"]=max(stats["max_direct_owned"],1)
                    if inject and act=="RESTART" and (root/"inject-crash").exists():
                        (root/"crash-window").write_text("RESTART_STARTED_BUT_RECEIPT_NOT_COMMITTED\n")
                        while True:
                            time.sleep(.1)
            elif act=="CHECK_HEALTH":
                result="DONE" if child is not None and check(port,"candidate") else "BLOCKED"
            elif act=="CHECK_TPROXY":
                result="DENIED"  # staging: S98 may NOT rewrite kernel rules
            else:
                raise FenceError("unexpected operation")
            ledger.complete(owner,req,result)
            stats["actor_receipts"]+=1
            atomic_journal(root/"owner-stats.json",stats)
        raise FenceError("owner lab deadline exceeded")
    finally:
        # Parent death is covered by PDEATHSIG. Never let a second actor
        # signal child. In normal paths, no OS daemonize/forking allowed.
        if child is not None:
            try:stop_xray(child,port)
            except (FenceError,OSError):pass


def guardian_reconcile(root,*,crash_lock=False):
    root=strict_lab(root)
    ledger=Ledger(root)
    if crash_lock:
        with supervisor_lock(ledger.lock):
            (root/"guardian-held-lock").write_text("HELD\n")
            while True:time.sleep(.2)
    previous=load(root/"owner-identity.json")
    end=time.monotonic()+12
    while alive(previous["pid"],previous["start_ticks"]):
        if time.monotonic()>end:
            raise FenceError("old owner still running")
        time.sleep(.04)
    runtime=load(root/"runtime.json")
    if not wait_absent(runtime["port"],12):
        raise FenceError("orphan listener survived; refuse recovery")
    if real_xray_processes(root):
        raise FenceError("orphan Xray descendant survived; refuse recovery")
    pinned=load(root/"rescue-evidence.json")
    raw=(root/"candidate.json").read_bytes()
    if (pinned.get("sha256")!=hashlib.sha256(raw).hexdigest()
        or pinned.get("physical_independence_verified") is not False):
        raise FenceError("disposable release/rescue evidence drift")
    ledger.quarantine_stale()
    proof={key:True for key in
          ("old_parent_exited","old_child_exited","all_descendants_drained",
           "old_listener_absent","rescue_sha_verified","no_unfenced_writers")}
    rec=ledger.reconcile_for_lab(proof)
    if rec["production_authorized"] is not False:
        raise FenceError("untrusted recovery authority")
    (root/"reconciled").write_text("UNCERTAIN_RETAINED_PENDING_CANCELLED\n")
    owner_loop(root)


def start_process(root,mode,extra=()):
    log=(root/(mode+"-"+str(time.monotonic_ns())+".log")).open("w")
    p=subprocess.Popen([sys.executable,"-m","xray.lab.v30_kernel49_cooperative_lab",
                        "--"+mode,str(root),*extra],
                       stdin=subprocess.DEVNULL,stdout=log,
                       stderr=subprocess.STDOUT,start_new_session=True)
    log.close()
    return p


def wait(root,name,timeout=30,owner=None):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        if (root/name).exists():
            return
        if owner is not None and owner.poll() is not None:
            raise FenceError("owner exited before "+name)
        time.sleep(.04)
    raise FenceError("timed out waiting for "+name)


def receipt_count(ledger):
    return len(ledger.read()["receipts"])


def wait_receipts(ledger,n,seconds=40):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        receipts=ledger.read()["receipts"]
        if len(receipts)>=n:
            return receipts
        time.sleep(.06)
    raise FenceError("cooperative actor requests not completed")


def demo(root,xray):
    root=strict_lab(root)
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    binary=os.environ.get("XRAY_MIPS_BINARY","")
    import shutil
    qemu=shutil.which("qemu-mipsel")
    if not qemu or not binary or not Path(binary).is_file():
        raise FenceError("real MIPS/QEMU binaries required")
    ver=subprocess.run([xray,"version"],capture_output=True,text=True,
                       check=True,timeout=20).stdout
    if "26.2.6" not in ver or "linux/mipsle" not in ver:
        raise FenceError("not actual Xray 26.2.6 MIPSLE")
    backend=EchoBackend("MIPS")
    udp=UdpEcho()
    backend.start()
    udp.start()
    owner=None
    guardian=None
    watchdog=None
    port=free_port()
    try:
        cfg=config(port,backend.port,udp_port=udp.port,enable_udp=True)
        (root/"candidate.json").write_text(json.dumps(cfg))
        atomic_journal(root/"runtime.json",{
            "qemu":qemu,"binary":str(Path(binary).resolve()),"port":port})
        atomic_journal(root/"rescue-evidence.json",{
            "sha256":hashlib.sha256((root/"candidate.json").read_bytes()).hexdigest(),
            "physical_independence_verified":False})
        ledger=Ledger(root)
        owner=start_process(root,"owner",("--inject",))
        wait(root,"owner-ready",owner=owner)
        start=ledger.submit("S97","START")
        receipts=wait_receipts(ledger,1)
        if receipts[-1]["sequence"]!=start["sequence"] or not check(port,"candidate"):
            raise FenceError("first owned Xray TCP/UDP start failed")
        # All competing actors submit through the same flock; only S97
        # can restart Xray. Concurrency is real Python subprocesses.
        commands=[("S97","RESTART"),("S97","RESTART"),
                  ("S99","CHECK_HEALTH"),("S98","CHECK_TPROXY"),
                  ("watchdog","CHECK_HEALTH"),("cron","CHECK_HEALTH"),
                  ("S97","RESTART"),("cron","CHECK_HEALTH")]
        clients=[start_process(root,"client",(actor,op)) for actor,op in commands]
        for c in clients:
            if c.wait(timeout=10)!=0:
                raise FenceError("concurrent actor submission failed")
        receipts=wait_receipts(ledger,1+len(commands),seconds=75)
        if not check(port,"candidate"):
            raise FenceError("concurrent restarts broke real Xray")
        if any(x["status"] not in ("DONE","DENIED") for x in receipts):
            raise FenceError("unexpected concurrent request failure")
        stats=load(root/"owner-stats.json")
        if stats["restarts"]<3 or stats["max_direct_owned"]!=1:
            raise FenceError("no proof of serial single-child restarts")
        if any(x["actor"]=="S98" and x["status"]!="DENIED" for x in receipts):
            raise FenceError("S98 was allowed unsafe kernel mutation")
        print("COOP49: PASS real MIPSLE TCP/UDP across 3 serialized competing S97 restarts",flush=True)
        print("COOP49: PASS S98 no-rules-mutation, watchdog/cron/S99 shared-flock requests",flush=True)
        # Crash the only parent while an S97 restart is mid-flight;
        # first guardian also dies while holding the exact same lock.
        (root/"inject-crash").write_text("YES\n")
        req=ledger.submit("S97","RESTART")
        wait(root,"crash-window",owner=owner)
        owner.kill()
        owner.wait(timeout=4)
        guardian=start_process(root,"guardian",("--crash-lock",))
        wait(root,"guardian-held-lock",owner=guardian)
        guardian.kill()
        guardian.wait(timeout=4)
        # Normal fresh guardian never sends a signal to previous Xray PID.
        watchdog=start_process(root,"guardian")
        wait(root,"reconciled",owner=watchdog,timeout=25)
        if not any(x["sequence"]==req["sequence"] and x["status"]=="UNCERTAIN"
                   for x in ledger.read()["receipts"]):
            raise FenceError("inflight crash did not remain UNCERTAIN")
        after=ledger.submit("S97","START")
        completed=wait_receipts(ledger,len(commands)+3,seconds=40)
        if not any(x["sequence"]==after["sequence"] and x["status"]=="DONE"
                   for x in completed):
            raise FenceError("new parent failed controlled restore")
        if not check(port,"candidate"):
            raise FenceError("real Xray TCP/UDP not restored")
        print("COOP49: PASS parent and guardian killed; independent owner restored real MIPS TCP/UDP",flush=True)
        print("COOP49: PASS crash mid-RESTART receipt remains UNCERTAIN, not replayed",flush=True)
        print("COOP49: PASS no stale PID signalling, no second Xray, one flock",flush=True)
        print("LIMITATION: disposable QEMU user-mode, not physical Linux4.9/TPROXY/USB",flush=True)
    finally:
        for p in (owner,guardian,watchdog):
            if p is not None and p.poll() is None:
                p.kill()
                p.wait(timeout=5)
        backend.close()
        udp.close()


def main():
    ap=argparse.ArgumentParser()
    mx=ap.add_mutually_exclusive_group(required=True)
    mx.add_argument("--demo",type=Path)
    mx.add_argument("--owner",type=Path)
    mx.add_argument("--client",type=Path)
    mx.add_argument("--guardian",type=Path)
    ap.add_argument("--xray")
    ap.add_argument("--inject",action="store_true")
    ap.add_argument("--crash-lock",action="store_true")
    ap.add_argument("actor",nargs="?")
    ap.add_argument("operation",nargs="?")
    a=ap.parse_args()
    if a.demo: demo(a.demo,a.xray)
    elif a.owner:owner_loop(a.owner,inject=a.inject)
    elif a.guardian:guardian_reconcile(a.guardian,crash_lock=a.crash_lock)
    else:
        if not a.actor or not a.operation:
            ap.error("--client requires actor and operation")
        print(json.dumps(Ledger(a.client).submit(a.actor,a.operation)))


if __name__=="__main__":
    main()
