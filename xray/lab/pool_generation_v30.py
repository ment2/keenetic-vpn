"""Offline generation/CAS state machine for v30 pool handover.

Prototype only: no filesystem, router, Xray API, network or credentials.
An actual controller must implement durable transaction journal, OS lock,
read-after-write verification, rollback and watchdog coordination.
"""
from dataclasses import dataclass
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


class Coordinator:
    def __init__(self, state: Generation):
        self.state = state

    def prepare(self, candidate: tuple[str, ...],
                failed: frozenset[str] = frozenset()) -> Proposal:
        return Proposal(self.state.number, candidate,
                        reconcile(self.state.pool, candidate, self.state.active, failed))

    def commit(self, proposal: Proposal, *, validated: bool, api_healthy: bool,
               continuity_verified: bool) -> Generation:
        if proposal.based_on != self.state.number:
            raise StaleGeneration("concurrent refresh superseded this proposal")
        if not validated or not api_healthy or not continuity_verified:
            raise UnsafeActivation("validation/API/continuity gate failed")
        if proposal.plan.action == "hold_fail_closed":
            # Do not commit an empty/disqualified pool.
            return self.state
        self.state = Generation(self.state.number + 1,
                                proposal.candidate, proposal.plan.selected)
        return self.state
