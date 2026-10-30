"""Pure first-migration safety model, NO router I/O.

Models exclusive SOCKS/TPROXY ingress ownership and watchdog fencing.
A legacy single-listener process cannot be replaced without a listener
ownership transition; this simulator does not claim zero interruption.
"""
from dataclasses import dataclass, replace


class MigrationRejected(RuntimeError):
    pass


@dataclass(frozen=True)
class State:
    generation: int = 0
    phase: str = "legacy"
    ingress_owner: str = "legacy"
    watchdog_fenced: bool = False
    legacy_alive: bool = True
    candidate_alive: bool = False
    candidate_api: bool = False
    candidate_validated: bool = False
    kill_switch: bool = True
    direct_fallback: bool = False
    active_tcp: int = 0


def invariant(s: State):
    if not s.kill_switch or s.direct_fallback:
        raise MigrationRejected("fail-closed policy violated")
    if s.ingress_owner not in ("legacy", "candidate", "none"):
        raise MigrationRejected("unknown ingress owner")
    if s.ingress_owner == "legacy" and not s.legacy_alive:
        raise MigrationRejected("ingress points at dead legacy process")
    if s.ingress_owner == "candidate" and not s.candidate_alive:
        raise MigrationRejected("ingress points at dead candidate")
    if s.phase in ("prepared", "cutover", "draining") and not s.watchdog_fenced:
        raise MigrationRejected("watchdog not fenced")
    return s


def prepare(s: State, *, expected_generation: int, validated: bool,
            api_healthy: bool, watchdog_fenced: bool):
    invariant(s)
    if s.phase != "legacy" or s.generation != expected_generation:
        raise MigrationRejected("stale or concurrent migration")
    if not validated or not api_healthy or not watchdog_fenced:
        raise MigrationRejected("candidate or watchdog gate failed")
    return invariant(replace(s, phase="prepared", candidate_alive=True,
                             candidate_api=True, candidate_validated=True,
                             watchdog_fenced=True))


def cutover(s: State, *, expected_generation: int, ingress_handoff_proven: bool):
    invariant(s)
    if s.phase != "prepared" or s.generation != expected_generation:
        raise MigrationRejected("stale or unprepared cutover")
    if not ingress_handoff_proven:
        raise MigrationRejected("no proven ingress ownership handoff")
    # Pure model: real socket handoff/conntrack continuity is NOT implemented.
    return invariant(replace(s, phase="draining", ingress_owner="candidate",
                             generation=s.generation + 1))


def finish(s: State, *, old_tcp_drained: bool, candidate_healthy: bool):
    invariant(s)
    if s.phase != "draining" or not old_tcp_drained or s.active_tcp:
        raise MigrationRejected("legacy still has active sessions")
    if not candidate_healthy:
        raise MigrationRejected("candidate failed verification")
    return invariant(replace(s, phase="api_enabled", legacy_alive=False,
                             watchdog_fenced=False))


def rollback(s: State, *, legacy_healthy: bool):
    invariant(s)
    if s.phase not in ("prepared", "draining"):
        raise MigrationRejected("rollback not applicable")
    if not legacy_healthy or not s.legacy_alive:
        raise MigrationRejected("cannot route to unhealthy legacy")
    return invariant(replace(s, phase="legacy", ingress_owner="legacy",
                             candidate_alive=False, candidate_api=False,
                             candidate_validated=False, watchdog_fenced=False,
                             generation=s.generation + 1))


def watchdog_action(s: State, *, socks_listener_healthy: bool):
    invariant(s)
    if s.watchdog_fenced:
        return "alert_only"
    if socks_listener_healthy:
        return "none"
    # Never invoke legacy S97xray restart/killall in migration controller.
    return "requires_explicit_recovery"
