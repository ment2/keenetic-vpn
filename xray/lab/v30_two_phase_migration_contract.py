#!/usr/bin/env python3
"""Review-only, two-phase v30 migration contract for the *actual* legacy actors.

This module emits a bounded sequence of release gates. It deliberately
cannot signal services, modify cron, install packages, or authorize deploy.
Real production migration requires independent owner approval of exact
paths/content and fresh, verified process identities while a common lock
protects all cooperating actors.
"""
import argparse
import json
from dataclasses import dataclass, fields
from pathlib import Path

from xray.lab.v30_release_manifest_contract import verify, MANIFEST

# These are exact archived legacy execution surfaces. A working program
# may be invoked via cron/service, so the set includes *indirect* writers.
LEGACY_ACTORS = (
    "S97xray", "S98xray-wifi", "S99xray-watchdog", "xray-watchdog.sh",
    "xray-wifi-rules.sh", "xray-fc-cron-guard.sh", "xray-safe-hourly.sh",
)
STAGES = (
    "PREPARE", "FREEZE_EXTERNAL_SPAWNERS", "DRAIN_DESCENDANTS",
    "STAGE_ALL_FILES", "VALIDATE", "ACTIVATE", "MONITOR", "COMMIT",
)


@dataclass(frozen=True)
class GateEvidence:
    fresh_live_pidfd_probe: bool = False
    cron_inventory_exact: bool = False
    service_boot_inventory_exact: bool = False
    all_external_spawners_cooperating: bool = False
    all_legacy_processes_identified_by_start_ticks: bool = False
    all_descendants_and_reparented_jobs_drained: bool = False
    kill_switch_pinned_and_non_usb: bool = False
    out_of_usb_rescue_mount_verified: bool = False
    out_of_usb_rescue_hashes_fsynced: bool = False
    recovery_guardian_boot_path_verified: bool = False
    staged_bundle_exact_sha_verified: bool = False
    no_legacy_unfenced_entrypoints: bool = False
    real_mips_kernel_tproxy_udp_tcp_verified: bool = False
    real_dns_ipv6_no_leak_verified: bool = False
    explicit_exact_release_owner_approval: bool = False


@dataclass(frozen=True)
class Snapshot:
    generation: int
    roots: tuple[tuple[int, int], ...]
    children: tuple[tuple[int, int, int], ...]
    orphan_writers: tuple[tuple[int, int], ...]
    cron_unknown: bool = True
    boot_unknown: bool = True


def inspect_snapshot(snapshot):
    problems = []
    if snapshot.generation <= 0:
        problems.append("INVALID_GENERATION")
    root_map = {}
    for pid, ticks in snapshot.roots:
        if pid <= 1 or ticks <= 0 or pid in root_map:
            problems.append("UNCERTAIN_LEGACY_ROOT")
        root_map[pid] = ticks
    seen = set(root_map)
    for pid, ppid, ticks in snapshot.children:
        if pid <= 1 or ticks <= 0 or pid in seen or ppid <= 0:
            problems.append("CHILD_IDENTITY_DRIFT")
        seen.add(pid)
        problems.append("UNFENCED_LEGACY_DESCENDANT")
    for pid, ticks in snapshot.orphan_writers:
        if pid <= 1 or ticks <= 0 or pid in seen:
            problems.append("UNVERIFIED_ORPHAN_PID")
        seen.add(pid)
        problems.append("ORPHANED_LEGACY_WRITER")
    if snapshot.roots:
        problems.append("LEGACY_ROOT_STILL_PRESENT")
    if snapshot.cron_unknown:
        problems.append("CRON_SPAWNER_INVENTORY_UNKNOWN")
    if snapshot.boot_unknown:
        problems.append("BOOT_SPAWNER_INVENTORY_UNKNOWN")
    return sorted(set(problems))


def phase_plan(evidence=GateEvidence(), snapshot=None):
    validation = verify()
    problems = ["NO_" + f.name.upper() for f in fields(GateEvidence)
                if getattr(evidence, f.name) is not True]
    if snapshot is None:
        problems.append("NO_FRESH_LIVE_PROCESS_SNAPSHOT")
    else:
        problems.extend(inspect_snapshot(snapshot))
    ready = not problems
    return {
        "schema": 1,
        "release": "v30-cooperative-supervisor-rc1",
        "manifest_verified": validation["verified"],
        "decision": "REVIEW_ONLY_NO_PRODUCTION_CHANGE",
        "deployment_authorized": False,
        "trial_authorized": False,
        "offline_gates_satisfied": ready,
        "reasons": sorted(set(problems)),
        "stages": list(STAGES),
        "legacy_spawner_surfaces": list(LEGACY_ACTORS),
        "rollback": {
            "before_activation": "restore originals only when all archive and external rescue hashes match",
            "after_activation": "independent protected recovery, then verify old Xray PID/ticks and kernel fail-closed",
            "on_identity_drift": "NO_SIGNAL; STOP; manual out-of-band recovery",
            "on_backup_loss": "NO_WRITE; retain kill-switch and request independent rescue",
        },
        "production_commands": [],
    }


def transition(stage, next_stage, *, evidence, snapshot):
    """Pure ordering gate; even successful contract is NOT deployment permission."""
    if stage not in STAGES or next_stage not in STAGES:
        raise ValueError("unknown two-phase stage")
    if STAGES.index(next_stage) != STAGES.index(stage) + 1:
        raise ValueError("phase skip or replay")
    report = phase_plan(evidence, snapshot)
    if report["reasons"]:
        raise ValueError("unverified real-world migration evidence")
    return {
        "from": stage, "to": next_stage,
        "transition": "OFFLINE_CONTRACT_ONLY",
        "deployment_authorized": False, "production_commands": [],
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--offline-plan", action="store_true")
    a=p.parse_args()
    if not a.offline_plan:
        p.error("only --offline-plan, no deployment/trial")
    print(json.dumps(phase_plan(), sort_keys=True))


if __name__ == "__main__":
    main()
