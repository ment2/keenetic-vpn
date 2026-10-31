"""RC12 fail-closed acceptance of evidence, never a router/spawner controller.

Synthetic all-green evidence is merely an offline review candidate. The actual
RC11 MIPS32LE Linux4.9 privileged cgroup v1 escape remains an observed blocker.
"""
from dataclasses import dataclass, fields
from typing import Tuple

ACTORS = (
    "S97xray", "S98xray-wifi", "S99xray-watchdog",
    "xray-watchdog.sh", "xray-wifi-rules.sh",
    "xray-fc-cron-guard.sh", "xray-safe-hourly.sh",
)

@dataclass(frozen=True)
class ActorWitness:
    name: str
    exact_live_sha256: bool = False
    boot_entrypoint_ack: bool = False
    cron_entrypoint_ack: bool = False
    watchdog_and_wifi_ack: bool = False
    locks_before_first_spawn: bool = False
    privileged_children_fenced_by_kernel: bool = False

@dataclass(frozen=True)
class Proof:
    actors: Tuple[ActorWitness, ...] = ()
    root_cgroup_escape_observed: bool = True
    no_out_of_scope_root_writer_proven: bool = False
    all_old_spawning_surfaces_prevented: bool = False
    complete_fork_exec_setsid_orphan_inventory: bool = False
    all_socket_inodes_and_pid_startticks_bootid_verified: bool = False
    no_pid_only_or_killall_signals: bool = False
    generation_cas_atomic_fsync_correct: bool = False
    prepared_generation_cannot_replay: bool = False
    stale_generation_cannot_write: bool = False
    guest_mips49_target_and_socket_modules_loaded: bool = False
    guest_mips49_tcp_packets_and_counters: bool = False
    guest_mips49_udp_packets_and_counters: bool = False
    guest_mips49_no_direct_fallback_after_kill: bool = False
    guest_ipv6_dns_no_leak: bool = False
    physical_vendor_ndm5_kernel_compatibility: bool = False
    independent_physical_rescue_power_domain: bool = False
    physical_usb_absent_cold_boot_and_corrupt_journal: bool = False
    physical_fsync_and_five_sha256_restore: bool = False

def evaluate(p: Proof):
    failures = []
    if tuple(a.name for a in p.actors) != ACTORS:
        failures.append("SEVEN_EXACT_LEGACY_SPAWNER_SURFACES_NOT_ATTESTED")
    if len({a.name for a in p.actors}) != len(p.actors):
        failures.append("DUPLICATE_OR_AMBIGUOUS_ACTOR")
    for a in p.actors:
        for f in fields(ActorWitness):
            if f.name != "name" and getattr(a, f.name) is not True:
                failures.append("LEGACY_ACTOR_UNFENCED:" + a.name + ":" + f.name)
    if p.root_cgroup_escape_observed:
        failures.append("OBSERVED_PRIVILEGED_CGROUP_V1_ESCAPE")
    for f in fields(Proof):
        if f.name not in ("actors", "root_cgroup_escape_observed") and getattr(p, f.name) is not True:
            failures.append("UNPROVEN:" + f.name)
    return {
        "decision": "HARD_NO_GO" if failures else "OFFLINE_REVIEW_CANDIDATE_ONLY",
        "reasons": sorted(set(failures)),
        "production_authorized": False,
        "hardware_accepted": False,
        "router_commands": [],
    }

def hypothetical_all_true_fixture():
    actors = tuple(ActorWitness(name, True, True, True, True, True, True)
                   for name in ACTORS)
    return Proof(actors=actors, root_cgroup_escape_observed=False, **{
        f.name: True for f in fields(Proof)
        if f.name not in ("actors", "root_cgroup_escape_observed")
    })
