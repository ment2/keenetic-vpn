"""Pure, offline pool reconciliation policy. Not wired to production Xray.

Endpoint keys are opaque fingerprints produced by a future canonicalizer.
No credentials, raw URLs, network, router access or process manipulation here.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class PoolPlan:
    keep_active: bool
    selected: str | None
    standby: tuple[str, ...]
    retired: tuple[str, ...]
    action: str
    reason: str


def reconcile(old: tuple[str, ...], new: tuple[str, ...],
              active: str | None, failed: frozenset[str] = frozenset()) -> PoolPlan:
    if len(set(old)) != len(old) or len(set(new)) != len(new):
        raise ValueError("duplicate endpoint fingerprint")
    if active is not None and active not in old:
        raise ValueError("active endpoint must belong to current pool")
    eligible = tuple(x for x in new if x not in failed)
    retired = tuple(x for x in old if x not in new)
    if active is not None and active in eligible:
        return PoolPlan(True, active, tuple(x for x in eligible if x != active),
                        retired, "keep", "active endpoint still qualified")
    if not eligible:
        return PoolPlan(bool(active is not None and active not in failed),
                        active if active not in failed else None, (), retired,
                        "hold_fail_closed", "no newly qualified endpoints")
    return PoolPlan(False, eligible[0], tuple(eligible[1:]), retired,
                    "switch_new_flows", "active absent or failed")
