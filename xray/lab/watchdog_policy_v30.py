#!/usr/bin/env python3
"""OFFLINE ONLY: PID-specific watchdog decision policy, no signals or router writes.

Safety boundary: this module can only return decisions. It never executes any
restart, kill, port redirection, route change, or firewall operation. The
current production S97xray 'killall xray' is *not* a valid recovery backend.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Identity:
    pid: int
    start_ticks: int

    def __post_init__(self):
        if self.pid <= 0 or self.start_ticks <= 0:
            raise ValueError("invalid process identity")


@dataclass(frozen=True)
class Observation:
    expected: Identity
    observed: Optional[Identity]
    phase: str = "steady"
    watchdog_fenced: bool = False
    lock_held: bool = False
    socks_ready: bool = True
    tproxy_tcp_ready: bool = True
    tproxy_udp_ready: bool = True
    kill_switch_verified: bool = True
    direct_fallback: bool = False
    journal_valid: bool = True
    generation_matches: bool = True


@dataclass(frozen=True)
class Decision:
    action: str
    reason: str
    sends_signal: bool = False
    changes_routes: bool = False


def decide(o: Observation) -> Decision:
    """Fail closed; avoid touching Xray on uncertain ownership or races.

    request_operator_recovery is a human escalation, NOT an executable action.
    In particular, no 'killall', PID-scoped kill, or automatic start is allowed.
    """
    if o.phase not in ("steady", "prepared", "switched", "draining", "rollback"):
        return Decision("block_new_flows", "unknown transaction phase")
    if not o.kill_switch_verified or o.direct_fallback:
        return Decision("block_new_flows", "kernel/direct fail-closed gate failed")
    if not o.journal_valid or not o.generation_matches:
        return Decision("block_new_flows", "journal or generation mismatch")
    if o.lock_held or o.watchdog_fenced or o.phase != "steady":
        return Decision("observe_only", "cutover/fence in progress; do not restart")
    if o.observed is None:
        return Decision("request_operator_recovery", "expected Xray absent; no automatic restart")
    if o.observed != o.expected:
        return Decision("block_new_flows", "PID/start-ticks changed; possible reuse")
    if not (o.socks_ready and o.tproxy_tcp_ready and o.tproxy_udp_ready):
        return Decision("request_operator_recovery", "one or more ingress protocols unavailable")
    return Decision("healthy", "all observed safety gates passed")
