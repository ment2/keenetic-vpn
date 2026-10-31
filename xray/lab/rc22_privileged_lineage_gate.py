"""RC22 read-only fail-closed legacy descendant graph evidence validation.

NEVER enumerates actual router processes or signals anything. In particular,
a passing synthetic graph is NOT proof of a privileged-kernel fence.
"""
from dataclasses import dataclass, replace
from typing import Tuple
import re

ACTORS=(
    "S97xray", "S98xray-wifi", "S99xray-watchdog",
    "xray-watchdog.sh", "xray-wifi-rules.sh",
    "xray-fc-cron-guard.sh", "xray-safe-hourly.sh",
)
SHA256=re.compile(r"^[0-9a-f]{64}$")

@dataclass(frozen=True)
class Entry:
    name: str
    live_sha256: str
    generation: int
    preboot_fenced: bool
    kernel_enforced: bool
    watchdog_cron_fenced: bool

@dataclass(frozen=True)
class Task:
    actor: str
    pid: int
    ppid: int
    start_ticks: int
    boot_id: str
    generation: int
    exe_sha256: str
    cgroup: str
    privileged: bool
    socket_inodes: Tuple[int,...]=()

@dataclass(frozen=True)
class Evidence:
    boot_id: str
    generation: int
    entries: Tuple[Entry,...]
    before: Tuple[Task,...]
    after: Tuple[Task,...]
    scope: str
    kernel_root_escape_absent_proven: bool
    independent_preboot_watcher_fencing: bool
    generation_cas_durable_and_exact: bool
    socket_inode_scan_complete: bool

def evaluate(e: Evidence):
    failures=[]
    if tuple(v.name for v in e.entries)!=ACTORS:
        failures.append("LEGACY_SEVEN_ENTRYPOINTS_NOT_EXACTLY_SEALED")
    if len({v.name for v in e.entries})!=len(e.entries):
        failures.append("LEGACY_DUPLICATE_ENTRYPOINT")
    if not e.boot_id or len(e.boot_id)!=36 or e.generation<1:
        failures.append("BOOT_ID_OR_GENERATION_INVALID")
    if not e.scope or e.scope=="/":
        failures.append("CGROUP_SCOPE_UNSEALED")
    for entry in e.entries:
        if entry.generation!=e.generation:
            failures.append("ENTRY_GENERATION_CAS_STALE:"+entry.name)
        if not SHA256.fullmatch(entry.live_sha256):
            failures.append("ENTRY_EXE_SHA256_UNKNOWN:"+entry.name)
        if not all((entry.preboot_fenced,entry.kernel_enforced,entry.watchdog_cron_fenced)):
            failures.append("ENTRY_PRIVILEGED_FENCE_UNPROVEN:"+entry.name)
    gates={
        "OBSERVED_ROOT_CGROUP_ESCAPE_NOT_INDEPENDENTLY_FENCED": e.kernel_root_escape_absent_proven,
        "INDEPENDENT_WATCHDOG_PREBOOT_GATE_MISSING": e.independent_preboot_watcher_fencing,
        "GENERATION_CAS_DURABILITY_UNPROVEN": e.generation_cas_durable_and_exact,
        "SOCKET_INODE_INVENTORY_UNPROVEN": e.socket_inode_scan_complete,
    }
    failures.extend(k for k,v in gates.items() if v is not True)
    before_by_pid={}
    seen_sockets=set()
    for stage,processes in (("BEFORE",e.before),("AFTER",e.after)):
        stage_identities=set()
        for p in processes:
            key=(p.pid,p.start_ticks,p.boot_id)
            if key in stage_identities:
                failures.append(stage+"_DUPLICATE_PID_STARTTICKS")
            stage_identities.add(key)
            if p.pid<=1 or p.ppid<=0 or p.start_ticks<=0 or not SHA256.fullmatch(p.exe_sha256):
                failures.append(stage+"_PROCESS_IDENTITY_MISSING")
            if p.actor not in ACTORS:
                failures.append(stage+"_UNKNOWN_LEGACY_DESCENDANT")
            if p.boot_id!=e.boot_id or p.generation!=e.generation:
                failures.append(stage+"_BOOT_OR_GENERATION_CAS_MISMATCH")
            if p.cgroup!=e.scope:
                failures.append(stage+"_DESCENDANT_ESCAPED_CGROUP")
            if p.privileged:
                failures.append(stage+"_PRIVILEGED_CHILD_NOT_FENCED")
            for inode in p.socket_inodes:
                if inode<=0:
                    failures.append(stage+"_INVALID_SOCKET_INODE")
                elif (stage,inode) in seen_sockets:
                    failures.append(stage+"_DUPLICATE_SOCKET_INODE")
                seen_sockets.add((stage,inode))
            if stage=="BEFORE":
                if p.pid in before_by_pid and before_by_pid[p.pid]!=key:
                    failures.append("BEFORE_PID_REUSE")
                before_by_pid[p.pid]=key
            elif p.pid in before_by_pid and before_by_pid[p.pid]!=key:
                failures.append("AFTER_PID_REUSE_OR_REBOOT")
        if stage=="AFTER" and processes:
            failures.append("LEGACY_DESCENDANTS_STILL_LIVE_OR_ZOMBIE")
    # No boolean, synthetic graph, or review can authorize production.
    return {
        "decision":"HARD_NO_GO" if failures else "OFFLINE_REVIEW_CANDIDATE_ONLY",
        "reasons":tuple(sorted(set(failures))),
        "production_authorized":False,
        "hardware_accepted":False,
        "router_commands":(),
    }

def synthetic_fixture():
    boot="00000000-1111-2222-3333-444444444444"
    entries=tuple(Entry(n,"a"*64,9,True,True,True) for n in ACTORS)
    return Evidence(boot,9,entries,(),(),"/disposable/rc22/gen9",
                    True,True,True,True)
