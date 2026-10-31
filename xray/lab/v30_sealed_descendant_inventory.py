#!/usr/bin/env python3
"""Offline sealed-scope process/socket inventory contract for Xray v30.

A double /proc scan cannot prove absence of arbitrary invisible descendants:
processes may daemonize, change argv/session and lose identifiable sockets.
A credible 'all descendants drained' assertion additionally needs a
previously sealed containment membership (e.g. independently verified cgroup
v1 on a kernel 4.9 installation). This contract never assumes that cgroup
exists or is writable on Keenetic.

The inventory is metadata-only synthetic/test evidence; NEVER signal PIDs.
"""
from dataclasses import dataclass
import hashlib
import json

class InventoryError(RuntimeError):
    pass

@dataclass(frozen=True)
class Member:
    pid: int
    ticks: int
    ppid: int
    executable: str
    argv: tuple[str, ...]
    socket_inodes: tuple[int, ...] = ()
    group: str = ""

@dataclass(frozen=True)
class Snapshot:
    generation: int
    scope_id: str
    members: tuple[Member, ...]
    open_socket_inodes: tuple[int, ...]
    unreadable_pids: tuple[int, ...] = ()
    membership_enumeration_complete: bool = False
    listener_enumeration_complete: bool = False
    scope_was_sealed_before_any_spawn: bool = False
    all_writers_in_same_scope: bool = False
    scope_kernel49_available: bool = False
    source: str = "SYNTHETIC"

def identity_digest(s):
    rows=[(m.pid,m.ticks,m.ppid,m.executable,m.argv,m.socket_inodes,m.group)
          for m in sorted(s.members,key=lambda m:(m.pid,m.ticks))]
    return hashlib.sha256(json.dumps([s.scope_id,rows,
        sorted(s.open_socket_inodes)],sort_keys=True).encode()).hexdigest()

def evaluate(first,second,*,direct_child=None,owner=None):
    blockers=[]
    if not isinstance(first,Snapshot) or not isinstance(second,Snapshot):
        raise InventoryError("two snapshots required")
    if first.generation<=0 or second.generation!=first.generation+1:
        blockers.append("NONCONSECUTIVE_SNAPSHOT_GENERATIONS")
    if first.scope_id!=second.scope_id or not first.scope_id:
        blockers.append("SCOPE_CHANGED_OR_UNKNOWN")
    if identity_digest(first)!=identity_digest(second):
        blockers.append("DOUBLE_SCAN_IDENTITY_DRIFT")
    for s in (first,second):
        if s.source!="SYNTHETIC":
            blockers.append("UNVERIFIED_EXTERNAL_SOURCE")
        if s.unreadable_pids:
            blockers.append("UNREADABLE_PROC_FD_OR_NET")
        if not s.membership_enumeration_complete:
            blockers.append("INCOMPLETE_CGROUP_MEMBERSHIP")
        if not s.listener_enumeration_complete:
            blockers.append("INCOMPLETE_TCP_UDP_INODE_INVENTORY")
        if not s.scope_was_sealed_before_any_spawn:
            blockers.append("UNSEALED_OR_UNTRUSTED_SCOPE")
        if not s.all_writers_in_same_scope:
            blockers.append("LEGACY_CRON_OR_RULE_WRITER_OUTSIDE_SCOPE")
        if not s.scope_kernel49_available:
            blockers.append("CGROUP_V1_SCOPE_NOT_VERIFIED_ON_KERNEL49")
        pids=set()
        for m in s.members:
            if m.pid<=1 or m.ticks<=0 or not m.executable or m.pid in pids:
                blockers.append("BAD_OR_REUSED_PID_IDENTITY")
            pids.add(m.pid)
            if m.group!=s.scope_id:
                blockers.append("PROCESS_ESCAPED_SEALED_SCOPE")
            if not m.argv:
                blockers.append("MISSING_EXECUTABLE_ARGUMENTS")
        owners=set()
        for m in s.members:
            owners.update(m.socket_inodes)
        if set(s.open_socket_inodes)-owners:
            blockers.append("UNATTRIBUTED_TCP_UDP_SOCKET")
        if len(s.open_socket_inodes)!=len(set(s.open_socket_inodes)):
            blockers.append("AMBIGUOUS_LISTENER_INODE")
        if owner is not None and any(m.pid==owner[0] and m.ticks!=owner[1]
                                     for m in s.members):
            blockers.append("OWNER_PID_REUSE")
        if direct_child is not None and any(m.pid==direct_child[0] and
                                           m.ticks!=direct_child[1] for m in s.members):
            blockers.append("DIRECT_CHILD_PID_REUSE")
        # Any member left in the sealed scope is a possible detached
        # descendant; scope membership must be EMPTY before recovery.
        if s.members:
            blockers.append("LIVE_SCOPE_MEMBER_OR_ORPHAN")
        if s.open_socket_inodes:
            blockers.append("SERVICE_TCP_UDP_SOCKET_STILL_OPEN")
    blockers=sorted(set(blockers))
    return {"status":"NO_RESTART" if blockers else "SYNTHETIC_DRAIN_CONTRACT_ONLY",
            "reason_codes":blockers,
            "independent_physical_inventory_proven":False,
            "production_recovery_authorized":False,
            "router_commands":[],
            "scope":first.scope_id}

def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--synthetic-check",action="store_true")
    a=p.parse_args()
    if not a.synthetic_check:p.error("no live router or /proc support")
    s=Snapshot(1,"v30-disposable",(),(),source="SYNTHETIC")
    t=Snapshot(2,"v30-disposable",(),(),source="SYNTHETIC")
    print(json.dumps(evaluate(s,t),sort_keys=True))

if __name__=="__main__":main()
