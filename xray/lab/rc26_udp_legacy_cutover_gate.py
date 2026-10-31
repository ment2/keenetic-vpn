"""RC26 evidence-only negative acceptance gate. No router I/O, no commands.

A positive disposable result is never a physical release authorization.
Real root cgroup-v1 escape and unavailable UDP hostfwd positive control
must remain blocking until independent evidence replaces them.
"""
from dataclasses import dataclass, fields
from typing import Tuple
from uuid import UUID
import re

ACTORS = ("S97xray", "S98xray-wifi", "S99xray-watchdog",
          "xray-watchdog.sh", "xray-wifi-rules.sh",
          "xray-fc-cron-guard.sh", "xray-safe-hourly.sh")
SHA = re.compile(r"^[0-9a-f]{64}$")

@dataclass(frozen=True)
class LegacyActor:
    name: str
    approved_sha256: str
    observed_sha256: str
    boot_acked: bool
    cron_acked: bool
    watchdog_acked: bool
    kernel_root_fence: bool
    no_stale_writer: bool

@dataclass(frozen=True)
class Process:
    pid: int
    ppid: int
    start_ticks: int
    boot_id: str
    exe_sha256: str
    generation: int
    socket_inodes: Tuple[int, ...]
    privileged: bool
    cgroup: str

@dataclass(frozen=True)
class Witness:
    actors: Tuple[LegacyActor, ...] = ()
    boot_id: str = ""
    scope: str = ""
    committed_generation: int = 0
    expected_generation: int = 0
    prepared_generation_replayed: bool = True
    root_cgroup_escape_observed: bool = True
    before: Tuple[Process, ...] = ()
    after: Tuple[Process, ...] = ()
    mips49_xt_tproxy_tcp_udp_backend: bool = False
    exact_host_udp_return_positive_control: bool = False
    original_destination_not_rewritten: bool = False
    distinct_backend_network_stack_proven: bool = False
    old_tcp_conntrack_established_before_cutover: bool = False
    old_tcp_survives_first_cutover_and_rollback: bool = False
    no_tcp_udp_direct_fallback_after_death: bool = False
    no_ipv4_ipv6_dns_leak: bool = False
    real_kernel_root_escape_fenced: bool = False
    physical_vendor_kernel_verified: bool = False
    independent_usb_absent_cold_boot_rescue: bool = False

def _uuid(value):
    try:
        return str(UUID(value)) == value and len(value) == 36
    except (ValueError, AttributeError, TypeError):
        return False

def evaluate(w: Witness):
    failures = []
    if tuple(a.name for a in w.actors) != ACTORS:
        failures.append("SEVEN_EXACT_LEGACY_ENTRYPOINTS_UNSEALED")
    if len({a.name for a in w.actors}) != len(w.actors):
        failures.append("DUPLICATE_LEGACY_ACTOR")
    for a in w.actors:
        if not SHA.fullmatch(a.approved_sha256) or not SHA.fullmatch(a.observed_sha256) or a.approved_sha256 != a.observed_sha256:
            failures.append("UNPINNED_OR_DRIFTED_LIVE_SHA:" + a.name)
        for f in fields(LegacyActor):
            if f.name not in ("name", "approved_sha256", "observed_sha256") and getattr(a, f.name) is not True:
                failures.append("UNFENCED_LEGACY_ACTOR:" + a.name + ":" + f.name)
    if not _uuid(w.boot_id):
        failures.append("BOOT_UUID_UNTRUSTED")
    if w.scope in ("", "/"):
        failures.append("CGROUP_SCOPE_NOT_SPECIFIC")
    if w.committed_generation <= 0 or w.expected_generation != w.committed_generation:
        failures.append("GENERATION_CAS_STALE_OR_AMBIGUOUS")
    if w.prepared_generation_replayed:
        failures.append("PREPARED_JOURNAL_REPLAY")
    if w.root_cgroup_escape_observed:
        failures.append("ACTUAL_PRIVILEGED_CGROUP_ESCAPE_OBSERVED")
    flags = ("mips49_xt_tproxy_tcp_udp_backend",
             "exact_host_udp_return_positive_control",
             "original_destination_not_rewritten",
             "distinct_backend_network_stack_proven",
             "old_tcp_conntrack_established_before_cutover",
             "old_tcp_survives_first_cutover_and_rollback",
             "no_tcp_udp_direct_fallback_after_death",
             "no_ipv4_ipv6_dns_leak", "real_kernel_root_escape_fenced",
             "physical_vendor_kernel_verified",
             "independent_usb_absent_cold_boot_rescue")
    for flag in flags:
        if getattr(w, flag) is not True:
            failures.append("UNPROVEN:" + flag)
    seen_before = {}
    for phase, procs in (("BEFORE", w.before), ("AFTER", w.after)):
        ids, socks = set(), set()
        for p in procs:
            key=(p.pid,p.boot_id,p.start_ticks)
            if p.pid <= 1 or p.ppid <= 1 or p.start_ticks <= 0 or not _uuid(p.boot_id) or p.boot_id != w.boot_id or not SHA.fullmatch(p.exe_sha256):
                failures.append(phase + "_PID_BOOT_START_SHA_INVALID")
            if p.generation != w.committed_generation:
                failures.append(phase + "_GENERATION_CAS_MISMATCH")
            if p.cgroup != w.scope or p.privileged:
                failures.append(phase + "_ROOT_OR_OUT_OF_SCOPE_CHILD")
            if key in ids:
                failures.append(phase + "_DUPLICATE_PID_STARTTICKS")
            ids.add(key)
            for inode in p.socket_inodes:
                if inode <= 0 or inode in socks:
                    failures.append(phase + "_SOCKET_INODE_UNRELIABLE")
                socks.add(inode)
            if phase == "BEFORE":
                if p.pid in seen_before and seen_before[p.pid] != key:
                    failures.append("BEFORE_PID_REUSE")
                seen_before[p.pid] = key
            elif p.pid in seen_before and seen_before[p.pid] != key:
                failures.append("AFTER_PID_REUSE_OR_BOOT_CHANGE")
        if phase == "AFTER" and procs:
            failures.append("ORPHAN_OR_LEGACY_DESCENDANT_NOT_DRAINED")
    return {
        "state": "HARD_NO_GO" if failures else "OFFLINE_REVIEW_CANDIDATE_ONLY",
        "reasons": tuple(sorted(set(failures))),
        "production_authorized": False,
        "hardware_certified": False,
        "real_packet_positive_control_accepted": False,
        "router_commands": (),
    }

def synthetic_all_positive():
    actors=tuple(LegacyActor(n, "a"*64,"a"*64,True,True,True,True,True) for n in ACTORS)
    opts=dict.fromkeys(("mips49_xt_tproxy_tcp_udp_backend",
             "exact_host_udp_return_positive_control",
             "original_destination_not_rewritten",
             "distinct_backend_network_stack_proven",
             "old_tcp_conntrack_established_before_cutover",
             "old_tcp_survives_first_cutover_and_rollback",
             "no_tcp_udp_direct_fallback_after_death",
             "no_ipv4_ipv6_dns_leak","real_kernel_root_escape_fenced",
             "physical_vendor_kernel_verified",
             "independent_usb_absent_cold_boot_rescue"), True)
    return Witness(actors=actors,boot_id="00000000-1111-2222-3333-444444444444",
                   scope="/rc26/offline",committed_generation=7,expected_generation=7,
                   prepared_generation_replayed=False,root_cgroup_escape_observed=False,
                   **opts)

def current_confirmed_evidence():
    """Sparse immutable known positive/negative witnesses only."""
    w=synthetic_all_positive()
    from dataclasses import replace
    return replace(w,
                   root_cgroup_escape_observed=True,
                   exact_host_udp_return_positive_control=False,
                   original_destination_not_rewritten=False,
                   distinct_backend_network_stack_proven=False,
                   old_tcp_conntrack_established_before_cutover=False,
                   old_tcp_survives_first_cutover_and_rollback=False,
                   no_ipv4_ipv6_dns_leak=False,
                   real_kernel_root_escape_fenced=False,
                   physical_vendor_kernel_verified=False,
                   independent_usb_absent_cold_boot_rescue=False)
