#!/usr/bin/env python3
"""STAGING LAB ONLY: cooperative Linux-4.9 Xray lifecycle request ledger.

S97, S98, S99, watchdog and cron only *request* operations under a shared
flock. One long-lived Xray direct parent alone may own/signal/reap a child.
A lock is NEVER held over the child's lifetime. Unknown startup/in-flight
operations are UNCERTAIN and NEVER replayed automatically. No router code,
iptables, signal, or actual production path is invoked by this module.
"""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import uuid

from xray.staging.v30_supervisor_core import FenceError, atomic_journal, supervisor_lock

ACTORS = {
    "S97": frozenset({"START","STOP","RESTART"}),
    "S98": frozenset({"CHECK_TPROXY"}),
    "S99": frozenset({"CHECK_HEALTH"}),
    "watchdog": frozenset({"CHECK_HEALTH"}),
    "cron": frozenset({"CHECK_HEALTH"}),
    "guardian": frozenset({"RECOVER"}),
}
SCHEMA = 1
STATE = "cooperative-ledger.json"
LOCK = "shared.lock"


def disposable(root):
    p=Path(root).resolve()
    if (not (str(p).startswith("/tmp/") or
             str(p).startswith("/home/runner/work/")) or
            Path("/opt/etc/xray/config.json").exists()):
        raise FenceError("LAB_ONLY; production forbidden")
    if p.is_symlink():
        raise FenceError("symlinked lab root")
    return p


def _fresh():
    return {"schema":SCHEMA,"sequence":0,"owner_generation":0,
            "owner":None,"pending":[],"inflight":None,"receipts":[],
            "blocked":False,"production_authorized":False}


class Ledger:
    def __init__(self,root):
        self.root=disposable(root)
        if not self.root.is_dir():
            raise FenceError("lab root missing")
        self.lock=self.root/LOCK
        self.state=self.root/STATE

    def _read(self):
        if self.state.is_symlink():
            raise FenceError("state symlink")
        if not self.state.exists():
            return _fresh()
        d=json.loads(self.state.read_text())
        if (d.get("schema")!=SCHEMA or d.get("production_authorized") is not False
            or not isinstance(d.get("pending"),list)
            or not isinstance(d.get("receipts"),list)
            or not isinstance(d.get("sequence"),int)
            or d["sequence"]<0):
            raise FenceError("corrupt or unsafe ledger")
        return d

    def read(self):
        with supervisor_lock(self.lock):
            return self._read()

    def _write(self,d):
        if d["production_authorized"] is not False:
            raise FenceError("production authorization never allowed")
        atomic_journal(self.state,d)

    def submit(self,actor,operation):
        if actor not in ACTORS or operation not in ACTORS[actor]:
            raise FenceError("actor operation denied")
        if actor=="guardian" and operation=="RECOVER":
            raise FenceError("guardian RECOVER requires separate recovery gate; no queued action")
        with supervisor_lock(self.lock):
            d=self._read()
            if d["blocked"]:
                raise FenceError("ledger blocked; manual reconciliation")
            if len(d["pending"])>=24:
                raise FenceError("bounded queue full")
            d["sequence"]+=1
            req={"sequence":d["sequence"],"actor":actor,"operation":operation}
            d["pending"].append(req)
            self._write(d)
            return req

    def open_owner(self,*,fresh_known_absence=False):
        """Must be called by a newly started direct parent before any spawn.

        Stale owner/inflight always BLOCKS. No PID-only lease expiry and no
        automatic takeover; the real guardian must independently prove
        old Xray absence (and absence of socket/listener/descendants).
        """
        with supervisor_lock(self.lock):
            d=self._read()
            if d["blocked"]:
                raise FenceError("manual reconciliation required")
            if d["owner"] is not None or d["inflight"] is not None:
                d["blocked"]=True
                if d["inflight"] is not None:
                    uncertain={**d["inflight"]["request"],"status":"UNCERTAIN"}
                    d["receipts"].append(uncertain)
                    d["inflight"]=None
                self._write(d)
                raise FenceError("stale owner/inflight; UNCERTAIN; manual recovery")
            if fresh_known_absence is not True:
                raise FenceError("unknown old process/listener/descendants")
            d["owner_generation"]+=1
            token=uuid.uuid4().hex
            d["owner"]={"generation":d["owner_generation"],"token":token,
                        "pid":os.getpid()}
            self._write(d)
            return d["owner"].copy()

    def claim(self,owner):
        with supervisor_lock(self.lock):
            d=self._read()
            if d["blocked"] or d["owner"]!=owner:
                raise FenceError("owner lease invalid; fail closed")
            if d["inflight"] is not None:
                raise FenceError("inflight cannot be claimed twice")
            if not d["pending"]:
                return None
            req=d["pending"].pop(0)
            d["inflight"]={"request":req,"owner_generation":owner["generation"]}
            self._write(d)
            return req

    def complete(self,owner,request,status):
        if status not in ("DONE","DENIED","BLOCKED"):
            raise FenceError("receipt cannot invent success")
        with supervisor_lock(self.lock):
            d=self._read()
            flight=d.get("inflight")
            if (d["blocked"] or d["owner"]!=owner or flight is None or
                flight["request"]!=request or
                flight["owner_generation"]!=owner["generation"]):
                raise FenceError("receipt owner/operation generation drift")
            d["receipts"].append({**request,"status":status})
            d["inflight"]=None
            self._write(d)

    def close_owner(self,owner,*,proved_child_absent=False):
        if proved_child_absent is not True:
            raise FenceError("never release owner with unknown child")
        with supervisor_lock(self.lock):
            d=self._read()
            if d["owner"]!=owner or d["inflight"] is not None:
                raise FenceError("owner drift or inflight")
            d["owner"]=None
            self._write(d)

    def quarantine_stale(self):
        """Recovery may mark stale requests UNCERTAIN, but never kill/replay."""
        with supervisor_lock(self.lock):
            d=self._read()
            if d["owner"] is None and d["inflight"] is None:
                return False
            d["blocked"]=True
            if d["inflight"] is not None:
                d["receipts"].append({**d["inflight"]["request"],
                                      "status":"UNCERTAIN"})
                d["inflight"]=None
            self._write(d)
            return True

    def reconcile_for_lab(self,proof):
        """Explicit offline-only rescue after a crashed owner.

        This accepts evidence of a *disposable process experiment* only,
        never a physical router proof. Already-queued calls are cancelled,
        not silently replayed by a new owner. No signalling occurs here.
        """
        required=("old_parent_exited","old_child_exited","all_descendants_drained",
                  "old_listener_absent","rescue_sha_verified",
                  "no_unfenced_writers")
        if not isinstance(proof,dict) or any(proof.get(key) is not True for key in required):
            raise FenceError("incomplete independent recovery evidence")
        with supervisor_lock(self.lock):
            d=self._read()
            if d["owner"] is None and not d["blocked"]:
                raise FenceError("not a crashed owner needing reconciliation")
            if d["inflight"] is not None:
                d["receipts"].append({**d["inflight"]["request"],
                                      "status":"UNCERTAIN"})
                d["inflight"]=None
            for req in d["pending"]:
                d["receipts"].append({**req,"status":"CANCELLED_UNCERTAIN"})
            d["pending"]=[]
            d["owner"]=None
            d["blocked"]=False
            self._write(d)
            return {"status":"OFFLINE_RECONCILED_ONLY","production_authorized":False}
