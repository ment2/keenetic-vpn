"""RC34 strict release gate: Linux conntrack tuple != Xray UDP session owner.

Pure offline acceptance contract. MIPS conntrack may retain an idle tuple,
but does not intrinsically identify the Xray process / UDP association,
ingress interface or guarantee complete timeout-free inventory. No commands.
"""
from dataclasses import dataclass
from ipaddress import ip_address

@dataclass(frozen=True)
class Identity:
    source: str
    sport: int
    destination: str
    dport: int
    protocol: str
    interface: str

@dataclass(frozen=True)
class Ownership:
    flow: Identity
    xray_pid: int
    start_ticks: int
    owner_generation: int
    boot_id: str
    socket_cookie: int

@dataclass(frozen=True)
class Evidence:
    boot_id: str
    generation: int
    kernel_conntrack: tuple[Identity,...]
    xray_session_inventory: tuple[Ownership,...]
    independent_client_sessions: tuple[Identity,...]
    kernel_owner_rule_receipts: tuple[Identity,...]
    no_packets_allowed_during_inventory_commit: bool=False
    durable_generation_cas_ack: bool=False
    exact_kernel_owner_cas_ack: bool=False
    independent_root_descendant_fence_ack: bool=False
    original_destination_preserved: bool=False
    old_tcp_udp_after_rollback: bool=False

def evaluate(e: Evidence):
    reasons=[]
    try:
        valid=all(
            v.protocol=="udp" and v.interface and 0<v.sport<=65535 and
            0<v.dport<=65535 and ip_address(v.source) and ip_address(v.destination)
            for v in e.independent_client_sessions+e.kernel_conntrack
        )
    except (ValueError,TypeError):
        valid=False
    if not valid:
        reasons.append("UDP_IDENTITY_INVALID_OR_MISSING_INTERFACE")
    clients=set(e.independent_client_sessions)
    kernel=set(e.kernel_conntrack)
    if not clients or len(clients)!=len(e.independent_client_sessions):
        reasons.append("INDEPENDENT_CLIENT_SESSION_INVENTORY_UNTRUSTED")
    if clients!=kernel:
        reasons.append("KERNEL_CONNTRACK_MISSED_OR_EXPIRED_UDP_ASSOCIATION")
    owners={r.flow:r for r in e.xray_session_inventory}
    if len(owners)!=len(e.xray_session_inventory) or set(owners)!=clients:
        reasons.append("XRAY_INTERNAL_UDP_SESSION_OWNER_INVENTORY_UNAVAILABLE")
    for flow, r in owners.items():
        if (r.xray_pid<=1 or r.start_ticks<=0 or r.socket_cookie<=0 or
            r.owner_generation!=e.generation or r.boot_id!=e.boot_id):
            reasons.append("SESSION_OWNER_PID_START_BOOT_GENERATION_INVALID")
    if set(e.kernel_owner_rule_receipts)!=clients:
        reasons.append("KERNEL_FLOW_OWNER_RULES_NOT_FULLY_ATTESTED")
    for name in ("no_packets_allowed_during_inventory_commit",
                 "durable_generation_cas_ack",
                 "exact_kernel_owner_cas_ack",
                 "independent_root_descendant_fence_ack",
                 "original_destination_preserved",
                 "old_tcp_udp_after_rollback"):
        if getattr(e,name) is not True:
            reasons.append("MISSING_ATOMIC_ACCEPTANCE:"+name)
    if not e.boot_id or e.generation<1:
        reasons.append("BOOT_OR_GENERATION_INVALID")
    return {
        "decision":"HARD_NO_GO" if reasons else "SYNTHETIC_CONTRACT_ONLY",
        "reasons":tuple(sorted(set(reasons))),
        "all_old_udp_sessions_proven":False,
        "physical_root_fence_proven":False,
        "production_authorized":False,
        "router_commands":(),
    }
