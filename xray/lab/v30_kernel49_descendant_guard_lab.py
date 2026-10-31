#!/usr/bin/env python3
"""Disposable grandchild survival adversarial lab for Linux4.9 supervisor.

An Xray-like child spawns a detached grandchild with TCP+UDP listener.
PDEATHSIG kills only the direct child, NOT the detached descendant.
Independent guardian therefore MUST block until the grandchild exits
cooperatively. No signals are ever sent to orphaned PIDs.
"""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

from xray.staging.v30_supervisor_core import FenceError, atomic_journal, proc_stat, supervisor_lock
from xray.staging.v30_kernel49_cooperative_ledger import Ledger
from xray.lab.v30_parent_owned_kernel49 import spawn_owned
from xray.lab.v30_mips_guardian_failover import alive, strict_lab
from xray.lab.xray_v30_api_continuity import free_port


def wait_file(path,seconds=8):
    until=time.monotonic()+seconds
    while time.monotonic()<until:
        if path.exists():
            return
        time.sleep(.04)
    raise FenceError("missing evidence "+str(path))


def listener(root):
    port=json.loads((root/"ports.json").read_text())["port"]
    with socket.socket() as tcp, socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as udp:
        tcp.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        tcp.bind(("127.0.0.1",port))
        udp.bind(("127.0.0.1",port))
        tcp.listen()
        tcp.settimeout(.15)
        udp.settimeout(.15)
        atomic_journal(root/"grandchild-identity.json",{
            "pid":os.getpid(),"ticks":proc_stat(os.getpid())[2],
            "kind":"detached_pdeathsig_does_not_propagate"})
        (root/"grandchild-ready").write_text("TCP_UDP_LISTENER\n")
        while not (root/"descendant-stop").exists():
            try:
                c,_=tcp.accept()
                c.sendall(b"ORPHAN")
                c.close()
            except socket.timeout:
                pass
            try:
                data,addr=udp.recvfrom(1024)
                udp.sendto(b"ORPHAN:"+data,addr)
            except socket.timeout:
                pass


def brancher(root):
    with (root/"brancher.log").open("w") as log:
        p=subprocess.Popen([sys.executable,"-m",
            "xray.lab.v30_kernel49_descendant_guard_lab",
            "--descendant",str(root)],
            stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
            start_new_session=True)
        log.flush()
    wait_file(root/"grandchild-ready")
    while True:time.sleep(.2)


def owner(root):
    ledger=Ledger(root)
    owner_rec=ledger.open_owner(fresh_known_absence=True)
    req=ledger.claim(owner_rec)
    if req is None or req["operation"]!="START":
        raise FenceError("owner expected S97 start")
    argv=[sys.executable,"-m","xray.lab.v30_kernel49_descendant_guard_lab",
          "--brancher",str(root)]
    with supervisor_lock(root/"shared.lock"):
        direct=spawn_owned(argv[0],argv,root/"brancher-prepared.json")
    atomic_journal(root/"owner-identity.json",{
        "pid":os.getpid(),"ticks":proc_stat(os.getpid())[2],
        "direct_child_pid":direct.pid,"direct_child_ticks":direct.ticks})
    wait_file(root/"grandchild-ready")
    ledger.complete(owner_rec,req,"DONE")
    (root/"owner-ready").write_text("OWNED_DIRECT_CHILD_SPAWNED_DETACHED_GRANDCHILD\n")
    while True:time.sleep(.2)


def probe(port):
    try:
        with socket.create_connection(("127.0.0.1",port),timeout=.5) as sock:
            if sock.recv(16)!=b"ORPHAN":return False
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as udp:
            udp.settimeout(.6)
            udp.sendto(b"UDP",("127.0.0.1",port))
            reply,_=udp.recvfrom(32)
            return reply==b"ORPHAN:UDP"
    except OSError:
        return False


def demo(root):
    root=strict_lab(root)
    root.mkdir(parents=True,mode=0o700,exist_ok=True)
    port=free_port()
    atomic_journal(root/"ports.json",{"port":port})
    ledger=Ledger(root)
    ledger.submit("S97","START")
    log=(root/"owner.log").open("w")
    parent=subprocess.Popen([sys.executable,"-m",
        "xray.lab.v30_kernel49_descendant_guard_lab","--owner",str(root)],
        stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
    log.close()
    try:
        wait_file(root/"owner-ready")
        identity=json.loads((root/"owner-identity.json").read_text())
        orphan=json.loads((root/"grandchild-identity.json").read_text())
        assert probe(port)
        parent.kill()
        parent.wait(timeout=4)
        end=time.monotonic()+6
        while alive(identity["direct_child_pid"],identity["direct_child_ticks"]):
            if time.monotonic()>end:
                raise FenceError("PDEATHSIG did not stop direct child")
            time.sleep(.04)
        if not alive(orphan["pid"],orphan["ticks"]) or not probe(port):
            raise FenceError("orphan scenario did not occur")
        print("DESCENDANT49: PASS direct child died but detached grandchild TCP+UDP remained",flush=True)
        ledger.quarantine_stale()
        denied=False
        proof={key:True for key in (
            "old_parent_exited","old_child_exited","all_descendants_drained",
            "old_listener_absent","rescue_sha_verified","no_unfenced_writers")}
        proof["all_descendants_drained"]=False
        proof["old_listener_absent"]=False
        try:ledger.reconcile_for_lab(proof)
        except FenceError:denied=True
        if not denied:
            raise FenceError("guardian wrongly approved live orphan")
        print("DESCENDANT49: PASS guardian refuses restart while orphan retains TCP+UDP",flush=True)
        # Self-terminating descendant, no os.kill(orphan_pid).
        (root/"descendant-stop").write_text("COOPERATIVE_SELF_EXIT\n")
        end=time.monotonic()+6
        while alive(orphan["pid"],orphan["ticks"]) or probe(port):
            if time.monotonic()>end:
                raise FenceError("cooperative grandchild failed to exit")
            time.sleep(.04)
        proof["all_descendants_drained"]=True
        proof["old_listener_absent"]=True
        report=ledger.reconcile_for_lab(proof)
        if report["production_authorized"] is not False:
            raise FenceError("lab proof must not authorize production")
        print("DESCENDANT49: PASS after voluntary orphan exit guardian can reconcile without PID signals",flush=True)
        print("LIMITATION: controlled test descendant; unknown background jobs on Keenetic remain NO-GO",flush=True)
    finally:
        (root/"descendant-stop").write_text("EXIT\n")
        if parent.poll() is None:
            parent.kill()
            parent.wait(timeout=3)


def main():
    p=argparse.ArgumentParser()
    group=p.add_mutually_exclusive_group(required=True)
    group.add_argument("--demo",type=Path)
    group.add_argument("--owner",type=Path)
    group.add_argument("--brancher",type=Path)
    group.add_argument("--descendant",type=Path)
    a=p.parse_args()
    if a.demo:demo(a.demo)
    elif a.owner:owner(strict_lab(a.owner))
    elif a.brancher:brancher(strict_lab(a.brancher))
    else:listener(strict_lab(a.descendant))


if __name__=="__main__":
    main()
