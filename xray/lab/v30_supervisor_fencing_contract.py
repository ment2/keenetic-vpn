#!/usr/bin/env python3
"""OFFLINE-ONLY v30 process-tree and cooperative-fencing release contract.

No router commands, signals, sockets, subprocess calls or mutations. This
module explicitly cannot authorize a live cutover by itself. It prevents the
incorrect assumption that SIGSTOP on a parent shell freezes descendants.
"""
from dataclasses import dataclass
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "xray" / "production" / "opt"
REQUIRED = (
    "cooperative_supervisor_lock",
    "cooperative_wifi_lock",
    "all_restart_paths_use_pid_scoped_signals",
    "descendant_barrier_proven",
    "atomic_candidate_identity_journal",
    "independent_recovery_guard_proven",
    "reboot_recovery_proven",
    "real_tproxy_tcp_udp_proven",
    "dns_ipv6_no_leak_proven",
)


@dataclass(frozen=True)
class Process:
    pid: int
    ppid: int
    start_ticks: int
    state: str
    role: str


@dataclass(frozen=True)
class Proof:
    cooperative_supervisor_lock: bool = False
    cooperative_wifi_lock: bool = False
    all_restart_paths_use_pid_scoped_signals: bool = False
    descendant_barrier_proven: bool = False
    atomic_candidate_identity_journal: bool = False
    independent_recovery_guard_proven: bool = False
    reboot_recovery_proven: bool = False
    real_tproxy_tcp_udp_proven: bool = False
    dns_ipv6_no_leak_proven: bool = False


def descendants(processes, root_pid):
    """Follow synthetic PPID links; fail closed on missing/duplicated identities."""
    by_pid = {}
    for p in processes:
        if p.pid <= 1 or p.start_ticks <= 0 or p.pid in by_pid:
            raise ValueError("invalid/ambiguous process identity")
        by_pid[p.pid] = p
    if root_pid not in by_pid:
        raise ValueError("root process identity not observed")
    found = set()
    frontier = [root_pid]
    while frontier:
        parent = frontier.pop()
        for p in processes:
            if p.ppid != parent or p.pid == root_pid:
                continue
            if p.pid in found:
                continue
            found.add(p.pid)
            frontier.append(p.pid)
    return tuple(by_pid[k] for k in sorted(found))


def unsafe_legacy_sources(*, watchdog, s97, s98, wifi_rules):
    """Static indicators from a frozen snapshot, not live process observations."""
    reasons = []
    if re.search(r'\bkillall\s+xray\b', s97):
        reasons.append("S97_GLOBAL_KILLALL")
    if re.search(r'\b(restart|start)\b', watchdog) and not (
            "flock" in watchdog and "transaction" in watchdog):
        reasons.append("WATCHDOG_NO_COOPERATIVE_MUTEX")
    if (re.search(r'\b(flush|iptables|XRAY_WIFI|xray-wifi-rules\.sh)\b', s98 + wifi_rules, re.I)
            and not ("flock" in s98 and "flock" in wifi_rules)):
        reasons.append("S98_RULES_MUTATE_WITHOUT_SHARED_MUTEX")
    if "-F" in wifi_rules and "XRAY_WIFI" in wifi_rules:
        reasons.append("WIFI_TPROXY_CHAIN_FLUSH")
    return tuple(sorted(set(reasons)))


def release_gate(proof, *, source_hazards=(), processes=(), watchdog_pid=None,
                 wifi_pid=None):
    missing = [name for name in REQUIRED if getattr(proof, name) is not True]
    blocked = list("UNPROVEN_" + name.upper() for name in missing)
    blocked.extend(source_hazards)
    if watchdog_pid is not None or wifi_pid is not None:
        if watchdog_pid is None or wifi_pid is None or watchdog_pid == wifi_pid:
            blocked.append("WATCHER_IDENTITY_UNCERTAIN")
        else:
            try:
                for root in (watchdog_pid, wifi_pid):
                    children = descendants(processes, root)
                    if children:
                        blocked.append("UNFENCED_DESCENDANTS")
                    watcher = next(p for p in processes if p.pid == root)
                    if watcher.state not in ("T", "t"):
                        blocked.append("WATCHER_NOT_ACTUALLY_STOPPED")
            except (ValueError, StopIteration):
                blocked.append("WATCHER_IDENTITY_UNCERTAIN")
    # Point-in-time process absence never substitutes for a shared lock.
    return tuple(sorted(set(blocked)))


def frozen_router_risks():
    get = lambda path: (SNAPSHOT / path).read_text(encoding="utf-8")
    return unsafe_legacy_sources(
        watchdog=get("bin/xray-watchdog.sh"),
        s97=get("etc/init.d/S97xray"),
        s98=get("etc/init.d/S98xray-wifi"),
        wifi_rules=get("bin/xray-wifi-rules.sh"),
    )


if __name__ == "__main__":
    reasons = release_gate(Proof(), source_hazards=frozen_router_risks())
    print(json.dumps({
        "decision": "NO_PRODUCTION_TRIAL",
        "reasons": reasons,
        "source": "FROZEN_GITHUB_SNAPSHOT_NOT_LIVE",
        "production_commands": [],
        "authorization": False,
    }, sort_keys=True))
