#!/usr/bin/env python3
"""Offline-only release gate for legacy S97/S98/S99/watchdog process trees.

A stopped shell PID is NOT proof that its descendants, reparented daemons or
cron-initiated jobs have stopped. This module never reads live /proc and never
sends signals. It only evaluates explicit synthetic/test evidence.
"""
from dataclasses import dataclass, fields
import json


@dataclass(frozen=True)
class Process:
    pid: int
    ppid: int
    start_ticks: int
    state: str
    command: str


@dataclass(frozen=True)
class Evidence:
    pidfd_kernel_supported: bool = False
    shared_flock_owned: bool = False
    all_legacy_entrypoints_disabled: bool = False
    legacy_watchdog_quiesced: bool = False
    wifi_writer_quiesced: bool = False
    cron_restart_jobs_quiesced: bool = False
    legacy_child_tree_drained: bool = False
    orphan_job_inventory_complete: bool = False
    full_legacy_restore_bundle_verified: bool = False
    durable_backup_survives_usb_failure: bool = False
    tproxy_tcp_udp_and_killswitch_verified: bool = False
    new_canary_matches_cooperative_version: bool = False
    independent_boot_recovery_verified: bool = False


LEGACY_MATCHES = (
    "/opt/etc/init.d/S97xray", "/opt/etc/init.d/S98xray-wifi",
    "/opt/etc/init.d/S99xray-watchdog", "/opt/bin/xray-watchdog.sh",
    "/opt/bin/xray-wifi-rules.sh", "killall xray",
)
UNFENCED_MATCHES = ("killall xray", "xray-wifi-rules.sh", "S97xray restart")


def process_hazards(snapshot, roots):
    """No PID-only trust; root reference is (pid, start_ticks)."""
    if not isinstance(snapshot, (list, tuple)) or not isinstance(roots, (list, tuple)):
        raise ValueError("missing bounded process snapshot")
    seen = {}
    for proc in snapshot:
        if (proc.pid <= 1 or proc.start_ticks <= 0 or
                proc.pid in seen or not proc.command or
                proc.state not in ("R", "S", "T", "t", "D", "Z", "X", "I")):
            raise ValueError("ambiguous process identity")
        seen[proc.pid] = proc
    roots_by_pid = {}
    for pid, ticks in roots:
        if pid in roots_by_pid or pid <= 1 or ticks <= 0:
            raise ValueError("duplicate/bad legacy root identity")
        roots_by_pid[pid] = ticks
        if pid not in seen or seen[pid].start_ticks != ticks:
            raise ValueError("legacy root PID reuse or snapshot incomplete")
    hazards = []
    active = lambda p: p.state not in ("Z", "X")
    for p in snapshot:
        if active(p) and any(term in p.command for term in UNFENCED_MATCHES):
            hazards.append("UNFENCED_EXECUTOR_PRESENT")
        if active(p) and any(term in p.command for term in LEGACY_MATCHES):
            hazards.append("LEGACY_ENTRYPOINT_PRESENT")
        if active(p) and p.ppid == 1 and any(term in p.command for term in LEGACY_MATCHES):
            hazards.append("ORPHANED_LEGACY_PROCESS")
    # Tree identities must include descendants, not just the root shell.
    frontier = list(roots_by_pid)
    descendants = set()
    while frontier:
        parent = frontier.pop()
        for p in snapshot:
            if p.ppid == parent and p.pid not in descendants:
                descendants.add(p.pid)
                frontier.append(p.pid)
    if any(active(seen[pid]) for pid in descendants):
        hazards.append("LIVE_LEGACY_DESCENDANTS")
    if any(active(seen[pid]) for pid in roots_by_pid):
        hazards.append("LEGACY_ROOTS_STILL_RUNNING")
    return tuple(sorted(set(hazards)))


def evaluate(snapshot, roots, *, evidence=Evidence(), inventory_complete=False):
    missing = ["MISSING_" + field.name.upper()
               for field in fields(Evidence) if getattr(evidence, field.name) is not True]
    if inventory_complete is not True:
        missing.append("INCOMPLETE_PROCESS_INVENTORY")
    try:
        missing.extend(process_hazards(snapshot, roots))
    except (ValueError, TypeError):
        missing.append("PROCESS_IDENTITY_UNCERTAIN")
    return {
        "decision": "NO_PRODUCTION_CUTOVER" if missing else "OFFLINE_CONTRACT_ONLY",
        "reason_codes": sorted(set(missing)),
        "production_cutover_authorized": False,
        "router_commands": [],
        "evidence_source": "SYNTHETIC_PROCESS_SNAPSHOT_ONLY",
    }


def main():
    result = evaluate([], [], evidence=Evidence(), inventory_complete=False)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
