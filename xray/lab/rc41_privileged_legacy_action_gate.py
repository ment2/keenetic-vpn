"""RC41 read-only legacy privileged action inventory and negative hardware gate.

Reads repository snapshots, never live router scripts or privileged processes.
Even all synthetic acknowledgements cannot replace kernel-enforced root fencing.
"""
from dataclasses import dataclass
from pathlib import Path
import hashlib
from .rc31_privileged_legacy_evidence_gate import SOURCES

ROOT=Path(__file__).resolve().parents[2]
EXECUTABLE_CAPABILITIES={
    "S97xray": ("killall xray",),
    "S98xray-wifi": ("while true", "xray-wifi-rules.sh"),
    "S99xray-watchdog": ("xray-watchdog.sh", '"$SCRIPT" >/dev/null 2>&1 &'),
    "xray-watchdog.sh": ("S97xray", '"$SERVICE" restart'),
    "xray-wifi-rules.sh": ('-t mangle -F "$CHAIN"', "ip route replace local default"),
    "xray-fc-cron-guard.sh": ("xray-fc-guard-enabled", "xray-fc-recover.sh"),
    "xray-safe-hourly.sh": ("PENDING=/opt/etc/xray/config.pending.json", "STAGED_ONLY:", "NOT applied"),
}
@dataclass(frozen=True)
class LegacyDescendantClaim:
    actor:str
    boot_id:str
    generation:int
    pid:int
    parent_pid:int
    start_ticks:int
    socket_cookie:int
    exec_sha256:str
    privileged:bool
    independently_kernel_denied:bool
    mandatory_kernel_receipt:bool
    escaped_cgroup:bool=False

def audit(root=ROOT,claims=(),expected_boot_id=None,expected_generation=None):
    reasons=["NO_ACTUAL_PHYSICAL_PRIVILEGED_ROOT_DESCENDANT_FENCE",
             "ROOT_CGROUP_V1_ESCAPE_RC11_REQUIRES_MANDATORY_KERNEL_FENCE",
             "NO_PHYSICAL_USB_FREE_COLD_BOOT_RESCUE",
             "NO_DURABLE_BOOT_GENERATION_CAS_ATOMIC_KERNEL_ACK"]
    snapshots={}
    if set(SOURCES)!=set(EXECUTABLE_CAPABILITIES) or len(SOURCES)!=7:
        reasons.append("LEGACY_SEVEN_SOURCE_INVENTORY_DRIFT")
    for actor,rel in SOURCES.items():
        p=Path(root)/rel
        if not p.is_file():
            reasons.append("VERSIONED_ROOT_ACTOR_SOURCE_MISSING:"+actor)
            continue
        body=p.read_bytes()
        digest=hashlib.sha256(body).hexdigest()
        snapshots[actor]={"sha256":digest,"runtime_executable_attested":False}
        for fragment in EXECUTABLE_CAPABILITIES.get(actor,()):
            if fragment.encode() not in body:
                reasons.append("LEGACY_ACTION_CAPABILITY_SOURCE_DRIFT:"+actor)
                break
        reasons.append("NO_INDEPENDENT_ROOT_DESCENDANT_DENIAL:"+actor)
    safe=(Path(root)/SOURCES["xray-safe-hourly.sh"])
    if safe.is_file():
        src=safe.read_text(encoding="utf-8")
        if '"$SERVICE" stop' in src or '"$SERVICE" start' in src:
            reasons.append("ACTIVE_SAFE_HOURLY_RESTART_CAPABILITY_REQUIRES_REAUDIT")
    claims=tuple(claims)
    claimed={e.actor for e in claims}
    if claimed!=set(SOURCES) or len(claims)!=7:
        reasons.append("SEVEN_LEGACY_ACTOR_DESCENDANT_RECEIPTS_MISSING_OR_DUPLICATE")
    if not expected_boot_id or not expected_generation or expected_generation<1:
        reasons.append("EXPECTED_BOOT_GENERATION_NOT_VERIFIED")
    for event in claims:
        if event.actor not in SOURCES:
            reasons.append("UNKNOWN_ROOT_DESCENDANT_ACTOR:"+event.actor)
        if event.boot_id!=expected_boot_id or event.generation!=expected_generation:
            reasons.append("ROOT_ACTOR_STALE_BOOT_OR_GENERATION:"+event.actor)
        if event.pid<=1 or event.parent_pid<=1 or event.start_ticks<=0 or event.socket_cookie<=0:
            reasons.append("ROOT_ACTOR_IDENTITY_OR_SOCKET_COOKIE_MISSING:"+event.actor)
        if (len(event.exec_sha256)!=64 or
            any(ch not in "0123456789abcdef" for ch in event.exec_sha256)):
            reasons.append("ROOT_ACTOR_EXEC_DIGEST_UNVERIFIED:"+event.actor)
        if not event.privileged or event.escaped_cgroup:
            reasons.append("ROOT_ACTOR_CGROUP_PRIVILEGE_BYPASS:"+event.actor)
        if not event.independently_kernel_denied or not event.mandatory_kernel_receipt:
            reasons.append("ROOT_ACTOR_KERNEL_DENIAL_MISSING:"+event.actor)
    return {
        "decision":"HARD_NO_GO_PRODUCTION",
        "reason_codes":tuple(sorted(set(reasons))),
        "versioned_files_sha256":snapshots,
        "privileged_root_fence_proven":False,
        "physical_rescue_proven":False,
        "kernel_freeze_commit_proven":False,
        "production_authorized":False,
        "router_actions":(),
    }
