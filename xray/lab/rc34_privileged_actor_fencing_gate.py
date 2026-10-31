"""RC34 negative read-only release gate for noncooperating privileged legacy actors.

NO process control; synthetic events are adversarial inputs, never evidence of
actual kernel enforcement. A passing offline gate cannot authorize production.
"""
from dataclasses import dataclass
from .rc31_privileged_legacy_evidence_gate import SOURCES

@dataclass(frozen=True)
class RestartAttempt:
    actor:str
    kind:str
    generation:int
    boot_id:str
    pid:int
    start_ticks:int
    privileged:bool
    kernel_denied:bool
    receipt_from_independent_kernel:bool
    escaped_cgroup:bool=False

def evaluate(events, *, boot_id, generation):
    reasons=["ACTUAL_ROUTER_KERNEL_FENCE_NOT_OBSERVED",
             "ROOT_CGROUP_V1_ESCAPE_NOT_CONTAINED_ON_HARDWARE"]
    if generation<1 or not boot_id:
        reasons.append("INVALID_BOOT_GENERATION")
    present={e.actor for e in events}
    if present!=set(SOURCES):
        reasons.append("SEVEN_ROOT_ENTRYPOINTS_NOT_COVERED")
    for e in events:
        if e.actor not in SOURCES:
            reasons.append("UNKNOWN_LEGACY_ACTOR:"+e.actor)
        if e.kind not in {"killall_xray","rewrite_tproxy","restart_s97","cron_restart","spawn_root","write_xray"}:
            reasons.append("UNRECOGNIZED_PRIVILEGED_ACTION:"+e.actor)
        if e.boot_id!=boot_id or e.generation!=generation:
            reasons.append("STALE_BOOT_OR_GENERATION:"+e.actor)
        if e.pid<=1 or e.start_ticks<=0:
            reasons.append("PID_START_TICKS_UNTRUSTED:"+e.actor)
        if e.escaped_cgroup:
            reasons.append("LEGACY_DESCENDANT_ESCAPED_CGROUP:"+e.actor)
        if not e.privileged:
            reasons.append("ACTOR_PRIVILEGE_UNVERIFIED:"+e.actor)
        if not e.kernel_denied or not e.receipt_from_independent_kernel:
            reasons.append("ROOT_ACTION_NOT_INDEPENDENTLY_DENIED:"+e.actor)
    return {
        "decision":"HARD_NO_GO_PRODUCTION",
        "reasons":tuple(sorted(set(reasons))),
        "live_fencing_proven":False,
        "release_authorized":False,
        "router_actions":(),
    }
