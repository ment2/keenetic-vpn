"""RC11 read-only legacy execution-surface fencing acceptance.

This consumes signed-off *synthetic/offline* evidence only. It never freezes,
signals, reads /proc, talks to Keenetic, or writes configuration. A complete
double /proc scan is not proof of containment: privileged processes can
escape cgroup v1, and S97/S98/S99/watchdog/cron may spawn out-of-scope.
"REVIEW_CANDIDATE" never means deploy authorization.
"""
from dataclasses import dataclass
from typing import Tuple
import hashlib

LEGACY_ACTORS = (
    "S97xray", "S98xray-wifi", "S99xray-watchdog",
    "xray-watchdog.sh", "xray-wifi-rules.sh",
    "xray-fc-cron-guard.sh", "xray-safe-hourly.sh",
)
# Frozen 5 original production-snapshot scripts, not live SHA attestations.
ARCHIVED_SHA = {
    "S97xray": "87ea1dc13a9be95d57c0595d7a7f13b03fe97bd56ab1f144a3c94d57cc588d5d",
    "S98xray-wifi": "6742e5e7f2a2bd41b85e9975371e7c46e66f0cfc6f5f843bf2c5dc1434c53601",
    "S99xray-watchdog": "e8423e15ed2cf4d3662e5725d27d6e58bd08bbdd807b47fcabe30391ac4c738b",
    "xray-watchdog.sh": "dddfcc1d324e30b91df041378645ada869a18b4d35f2842383e5d319fc859e08",
    "xray-wifi-rules.sh": "ead5de5555aaab1170a140ca3d41ea546330a99ba873b1961bee536bc12780ef",
}
BOOT = "00000000-1111-2222-3333-444444444444"  # synthetic fixture ONLY

@dataclass(frozen=True)
class Actor:
    name: str
    exact_sha256: str
    old_spawner_inhibited: bool
    boot_trigger_inhibited: bool
    cron_trigger_inhibited: bool
    no_privileged_escaping_child: bool
    ack_under_common_flock: bool

@dataclass(frozen=True)
class Process:
    pid: int
    start_ticks: int
    boot_id: str
    cgroup: str
    socket_inodes: Tuple[int, ...] = ()
    exact_exe_sha256: str = ""
    privileged: bool = False

@dataclass(frozen=True)
class Evidence:
    boot_id: str
    guardian_generation: int
    expected_generation: int
    actors: Tuple[Actor, ...]
    snapshot_before: Tuple[Process, ...]
    snapshot_after: Tuple[Process, ...]
    cgroup_scope: str
    cgroup_sealed_before_first_spawn: bool
    cgroup_v1_available: bool
    cgroup_membership_enumeration_complete: bool
    socket_inode_enumeration_complete: bool
    kernel_capability_boundary_verified: bool
    privileged_escape_absent_proven: bool
    unknown_orphan_absent_proven: bool
    socket_listeners_fenced: bool
    no_global_killall_or_pid_only_kill: bool
    guardian_crash_prepared_not_committed: bool
    independent_boot_rescue_integrity: bool
    physical_ndm5_mips_tproxy_no_leak_verified: bool
    exact_live_sha_verified: bool

@dataclass(frozen=True)
class Decision:
    status: str
    reasons: Tuple[str, ...]
    deployment_authorized: bool = False

def evaluate(e: Evidence) -> Decision:
    problems = []
    if not e.boot_id or len(e.boot_id) != 36:
        problems.append("BOOT_ID_UNKNOWN")
    if e.guardian_generation <= 0 or e.guardian_generation != e.expected_generation:
        problems.append("STALE_OR_AMBIGUOUS_GUARDIAN_GENERATION")
    if tuple(a.name for a in e.actors) != LEGACY_ACTORS:
        problems.append("SEVEN_LEGACY_SURFACES_NOT_EXACTLY_INVENTORIED")
    if len({a.name for a in e.actors}) != len(e.actors):
        problems.append("DUPLICATE_LEGACY_ACTOR")
    for a in e.actors:
        if a.name in ARCHIVED_SHA and a.exact_sha256 != ARCHIVED_SHA[a.name]:
            problems.append("ARCHIVE_SCRIPT_SHA_CHANGED:" + a.name)
        if not all((a.old_spawner_inhibited, a.boot_trigger_inhibited,
                    a.cron_trigger_inhibited, a.no_privileged_escaping_child,
                    a.ack_under_common_flock)):
            problems.append("ACTOR_REMAINS_ACTIVE_OR_UNFENCED:" + a.name)
    hard_gates = {
        "CGROUP_V1_NOT_VERIFIED": e.cgroup_v1_available,
        "CGROUP_NOT_SEALED_PRIOR_TO_SPAWN": e.cgroup_sealed_before_first_spawn,
        "MEMBERSHIP_ENUMERATION_UNTRUSTED": e.cgroup_membership_enumeration_complete,
        "SOCKET_INODE_SCAN_INCOMPLETE": e.socket_inode_enumeration_complete,
        "CAPABILITY_BOUNDARY_NOT_PROVEN": e.kernel_capability_boundary_verified,
        "PRIVILEGED_CGROUP_ESCAPE_POSSIBLE": e.privileged_escape_absent_proven,
        "UNKNOWN_REPARENTED_ORPHAN_NOT_FENCED": e.unknown_orphan_absent_proven,
        "TCP_UDP_SOCKETS_NOT_FENCED": e.socket_listeners_fenced,
        "GLOBAL_KILLALL_OR_PID_ONLY_KILL_RISK": e.no_global_killall_or_pid_only_kill,
        "PREPARED_GENERATION_CRASH_CAN_REPLAY": e.guardian_crash_prepared_not_committed,
        "BOOT_RESCUE_NOT_INDEPENDENT": e.independent_boot_rescue_integrity,
        "PHYSICAL_MIPS_NDM5_NOLEAK_UNPROVEN": e.physical_ndm5_mips_tproxy_no_leak_verified,
        "CURRENT_LIVE_SHA_NOT_ATTESTED": e.exact_live_sha_verified,
    }
    problems.extend(reason for reason, ok in hard_gates.items() if not ok)
    if not e.cgroup_scope or e.cgroup_scope == "/":
        problems.append("SCOPE_UNKNOWN_OR_GLOBAL")
    for which, snapshot in (("BEFORE",e.snapshot_before),("AFTER",e.snapshot_after)):
        identities = set()
        for p in snapshot:
            key = (p.boot_id,p.pid,p.start_ticks)
            if p.pid <= 1 or p.start_ticks <= 0 or p.boot_id != e.boot_id or not p.exact_exe_sha256:
                problems.append(which + "_PID_STARTTICKS_BOOT_EXE_IDENTITY_UNKNOWN")
            if p.cgroup != e.cgroup_scope:
                problems.append(which + "_DESCENDANT_OUTSIDE_SEALED_SCOPE")
            if p.privileged:
                problems.append(which + "_ROOT_OR_PRIVILEGED_DESCENDANT")
            if key in identities:
                problems.append(which + "_DUPLICATE_PID_IDENTITY")
            identities.add(key)
            if p.socket_inodes and not e.socket_listeners_fenced:
                problems.append(which + "_UNFENCED_SOCKET_INODE")
    older = {p.pid:(p.boot_id,p.start_ticks) for p in e.snapshot_before}
    for p in e.snapshot_after:
        if p.pid in older and older[p.pid] != (p.boot_id,p.start_ticks):
            problems.append("PID_REUSE_OR_BOOT_EPOCH_CHANGED")
    if e.snapshot_after:
        problems.append("DESCENDANTS_STILL_RUNNING_OR_ZOMBIE")
    # Even a perfectly formed synthetic review is not a production approval.
    return Decision("HARD_NO_GO" if problems else "OFFLINE_REVIEW_CANDIDATE_ONLY",
                    tuple(sorted(set(problems))),False)

def offline_good_fixture() -> Evidence:
    actors = tuple(Actor(name,ARCHIVED_SHA.get(name,"0"*64),
                         True,True,True,True,True) for name in LEGACY_ACTORS)
    return Evidence(
        BOOT,7,7,actors,(),(),"/rc11/test-gen-7",
        True,True,True,True,True,True,True,True,True,True,True,True,True,
    )
