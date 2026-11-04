"""RC37 offline reconciliation of live, pending and qualified Xray configurations.

Decision-making only. Never touches a router or runs Xray, and never
authorizes production cutover based on simulated evidence.

This explicitly fixes the *reasoning* bug where an unchanged pending file was
mistaken for an already applied live configuration. Applying it remains a
separate physical release gate requiring independently verified continuity.
"""
from dataclasses import dataclass
import json

from xray.lab.pool_reconcile_v30 import reconcile


BLOCKERS = (
    "API_LESS_LEGACY_FIRST_MIGRATION",
    "XRAY_UDP_OWNER_INVENTORY_INCOMPLETE",
    "ATOMIC_KERNEL_INGRESS_FREEZE_COMMIT_UNPROVEN",
    "PRIVILEGED_S97_S98_S99_WATCHDOG_CRON_NOT_FENCED",
    "VENDOR_KERNEL_AND_PHYSICAL_RESCUE_NOT_ACCEPTED",
    "DNS_IPV6_NO_LEAK_NOT_VERIFIED",
    "DURABLE_GENERATION_CAS_AND_ROLLBACK_NOT_VERIFIED",
)


@dataclass(frozen=True)
class PoolReview:
    decision: str
    reason: str
    candidate_equal_to_live: bool
    candidate_equal_to_pending: bool | None
    old_tags: tuple[str, ...]
    qualified_tags: tuple[str, ...]
    removed_tags: tuple[str, ...]
    added_tags: tuple[str, ...]
    identity_conflicts: tuple[str, ...]
    active_endpoint_known: bool
    release_blockers: tuple[str, ...]
    production_authorized: bool = False
    router_commands: tuple = ()


def _decode(raw):
    if not isinstance(raw, (str, bytes, bytearray)):
        raise ValueError("invalid config bytes")
    config = json.loads(raw)
    if not isinstance(config, dict):
        raise ValueError("config must be a mapping")
    return config


def _qualified(config):
    outbounds = config.get("outbounds", [])
    if not isinstance(outbounds, list):
        raise ValueError("missing outbounds")
    values = {}
    for outbound in outbounds:
        if outbound.get("protocol") != "vless":
            continue
        tag = outbound.get("tag")
        if not isinstance(tag, str) or not tag.startswith("vpn") or tag in values:
            raise ValueError("duplicate or invalid VLESS tag")
        # Exact transport, TLS/REALITY and client credentials matter for
        # continuity. This identity stays *private in memory* and is never
        # printed, saved, or sent to GitHub.
        identity = json.dumps(
            {k: v for k, v in outbound.items() if k != "tag"},
            sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        )
        values[tag] = identity
    return values


def review(live_raw, candidate_raw, pending_raw=None, *, active_tag=None,
           observed_live_owner=False):
    live, candidate = _decode(live_raw), _decode(candidate_raw)
    pending = _decode(pending_raw) if pending_raw is not None else None
    old = _qualified(live)
    new = _qualified(candidate)
    if not new:
        return PoolReview(
            "REJECT_CANDIDATE", "EMPTY_QUALIFIED_POOL", False,
            pending is not None and pending == candidate if pending is not None else None,
            tuple(sorted(old)), (), tuple(sorted(old)), (), (), False, BLOCKERS,
        )
    fallback = [
        b.get("fallbackTag") for b in candidate.get("routing", {}).get("balancers", [])
        if b.get("fallbackTag") is not None
    ]
    if any(tag not in new for tag in fallback):
        return PoolReview(
            "REJECT_CANDIDATE", "FALLBACK_OUTSIDE_QUALIFIED_POOL", False,
            pending == candidate if pending is not None else None,
            tuple(sorted(old)), tuple(sorted(new)), (), (), (), False, BLOCKERS,
        )
    equal = live == candidate
    pending_equal = pending == candidate if pending is not None else None
    added = tuple(sorted(set(new) - set(old)))
    removed = tuple(sorted(set(old) - set(new)))
    reuse = tuple(sorted(tag for tag in set(old) & set(new) if old[tag] != new[tag]))
    active_known = bool(observed_live_owner and active_tag in old)
    if equal:
        return PoolReview(
            "SKIP_UNCHANGED", "CANDIDATE_EQUALS_LIVE", True, pending_equal,
            tuple(sorted(old)), tuple(sorted(new)), (), (), (), active_known, (),
        )
    if reuse:
        reason = "TAG_REUSED_FOR_DIFFERENT_ENDPOINT"
    elif not active_known:
        reason = "ACTUAL_ACTIVE_ENDPOINT_UNOBSERVED"
    else:
        # The policy module is called with private exact identities; no
        # endpoint ID or credentials escape this output.
        plan = reconcile(tuple(old.values()), tuple(new.values()), old[active_tag])
        reason = "STAGED_" + plan.action.upper()
    return PoolReview(
        "APPLY_REQUIRED_BUT_BLOCKED", reason, False, pending_equal,
        tuple(sorted(old)), tuple(sorted(new)), removed, added, reuse,
        active_known, BLOCKERS,
    )


def sanitized_dict(result):
    return {
        "decision": result.decision,
        "reason": result.reason,
        "candidate_equal_to_live": result.candidate_equal_to_live,
        "candidate_equal_to_pending": result.candidate_equal_to_pending,
        "old_tags": list(result.old_tags),
        "qualified_tags": list(result.qualified_tags),
        "removed_tags": list(result.removed_tags),
        "added_tags": list(result.added_tags),
        "identity_conflicts": list(result.identity_conflicts),
        "active_endpoint_known": result.active_endpoint_known,
        "release_blockers": list(result.release_blockers),
        "production_authorized": False,
        "router_commands": [],
    }


def main():
    # Explicitly synthetic demonstration. A green result is NOT a release.
    old = {"outbounds": [{"protocol": "vless", "tag": t}
           for t in ("vpn01", "vpn02", "vpn04", "vpn05", "vpn06", "vpn07", "vpn09")]}
    new = {"outbounds": [{"protocol": "vless", "tag": t}
           for t in ("vpn01", "vpn02", "vpn04", "vpn05", "vpn09")]}
    result = review(json.dumps(old), json.dumps(new), json.dumps(new))
    print(json.dumps(sanitized_dict(result), sort_keys=True))


if __name__ == "__main__":
    main()
