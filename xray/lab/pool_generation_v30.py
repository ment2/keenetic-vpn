"""Offline generation/CAS state machine for v30 pool handover.

Prototype only: no router, Xray API, filesystem, credentials or network.
Not sufficient for production until durable locked journaling, proof of
real API completion, independent health, and watchdog fencing exist.
"""
from dataclasses import dataclass
from threading import RLock
from .pool_reconcile_v30 import reconcile, PoolPlan


class StaleGeneration(RuntimeError):
    pass


class UnsafeActivation(RuntimeError):
    pass


@dataclass(frozen=True)
class Generation:
    number: int
    pool: tuple[str, ...]
    active: str | None


@dataclass(frozen=True)
class Proposal:
    based_on: int
    candidate: tuple[str, ...]
    plan: PoolPlan
    failed: frozenset[str] = frozenset()


class Coordinator:
    """In-memory concurrency-safe CAS of verified pool identities only."""

    def __init__(self, state: Generation):
        if state.number < 1 or len(state.pool) != len(set(state.pool)):
            raise ValueError("invalid starting generation")
        if state.active is not None and state.active not in state.pool:
            raise ValueError("active must be part of old qualified pool")
        self.state = state
        self._lock = RLock()

    def prepare(self, candidate: tuple[str, ...],
                failed: frozenset[str] = frozenset()) -> Proposal:
        with self._lock:
            # Store immutable snapshots: caller's input can never modify a
            # previously prepared proposal by mutating a list/set afterwards.
            candidate = tuple(candidate)
            failed = frozenset(failed)
            plan = reconcile(self.state.pool, candidate, self.state.active, failed)
            return Proposal(self.state.number, candidate, plan, failed)

    def commit(self, proposal: Proposal, *, validated: bool, api_healthy: bool,
               continuity_verified: bool) -> Generation:
        with self._lock:
            if proposal.based_on != self.state.number:
                raise StaleGeneration("concurrent refresh superseded this proposal")
            # A plan cannot be forged or transplanted from a different candidate:
            # recompute under the same generation and exact failed set.
            if not isinstance(proposal.candidate, tuple) or not isinstance(proposal.failed, frozenset):
                raise UnsafeActivation("mutable/ambiguous proposal")
            try:
                expected = reconcile(self.state.pool, proposal.candidate,
                                     self.state.active, proposal.failed)
            except (ValueError, TypeError) as exc:
                raise UnsafeActivation("invalid proposal candidate") from exc
            if proposal.plan != expected:
                raise UnsafeActivation("proposal no longer matches qualified pool or active owner")
            if not validated or not api_healthy or not continuity_verified:
                raise UnsafeActivation("validation/API/continuity gate failed")
            if expected.action == "hold_fail_closed":
                # Do not mutate last-known-good when no new healthy pool exists.
                # Actual ingress owner MUST independently fail closed if dead.
                return self.state
            qualified = tuple(x for x in proposal.candidate if x not in proposal.failed)
            if not qualified or expected.selected not in qualified:
                raise UnsafeActivation("selected endpoint is not currently qualified")
            # Store only qualified IDs. Keep retired flows alive separately at
            # the Xray/session layer: this model NEVER stops old processes.
            self.state = Generation(self.state.number + 1,
                                    qualified, expected.selected)
            return self.state
