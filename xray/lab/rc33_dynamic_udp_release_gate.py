"""RC33 release gate: a bounded packet observer cannot certify silent UDP flows.

Pure offline, never a router command. A snapshot's old/new classification
must be checked against an independent pre-cutover socket inventory, an actual
per-rule kernel witness and the same boot/generation. Still NEVER production.
"""
from dataclasses import dataclass
from ipaddress import ip_address
@dataclass(frozen=True,order=True)
class Flow:
    source:str
    sport:int
    destination:str
    dport:int
    protocol:str
    interface:str
@dataclass(frozen=True)
class Evidence:
    boot_id:str=""
    observed_boot_id:str=""
    generation:int=0
    observed_generation:int=0
    old_client_sockets:tuple=()
    captured_incoming:tuple=()
    old_kernel_owner_rules:tuple=()
    new_kernel_owner_packets:int=0
    rollback_old_socket_bytes_proven:bool=False
    old_xray_pid_startticks_preserved:bool=False
    new_xray_pid_startticks_preserved:bool=False
    physically_fenced_seven_privileged_legacy:bool=False
    vendor_kernel_live_verified:bool=False
    usb_independent_physical_rescue:bool=False

def _valid(f):
    if not isinstance(f,Flow):return False
    try:
        ip_address(f.source);ip_address(f.destination)
    except ValueError:
        return False
    return (f.protocol=="udp" and f.interface=="eth1" and
            1024<=f.sport<=65535 and f.dport==19301)

def evaluate(e):
    reasons=[]
    if not e.boot_id or e.observed_boot_id != e.boot_id:
        reasons.append("BOOT_ID_CAS_NOT_ATTESTED")
    if e.generation<=0 or e.observed_generation!=e.generation:
        reasons.append("GENERATION_CAS_NOT_ATTESTED")
    original=e.old_client_sockets
    received=e.captured_incoming
    if not original or not all(_valid(f) for f in original+received):
        reasons.append("UNBOUNDED_OR_INVALID_UDP_IDENTITY")
    if len(set(original))!=len(original) or len(set(received))!=len(received):
        reasons.append("DUPLICATE_UDP_FIVE_TUPLE")
    if set(original)!=set(received):
        reasons.append("SILENT_OR_UNOBSERVED_OLD_UDP_ASSOCIATION")
    if set(original)!=set(e.old_kernel_owner_rules):
        reasons.append("OLD_UDP_KERNEL_OWNERSHIP_UNPROVEN")
    if e.new_kernel_owner_packets<1:
        reasons.append("NEW_UDP_CANDIDATE_OWNER_UNPROVEN")
    for attr in ("rollback_old_socket_bytes_proven",
                 "old_xray_pid_startticks_preserved",
                 "new_xray_pid_startticks_preserved"):
        if getattr(e,attr) is not True:
            reasons.append("MISSING_"+attr.upper())
    for attr in ("physically_fenced_seven_privileged_legacy",
                 "vendor_kernel_live_verified",
                 "usb_independent_physical_rescue"):
        if getattr(e,attr) is not True:
            reasons.append("PHYSICAL_HARD_NO_GO:"+attr)
    return {
      "decision":"HARD_NO_GO" if reasons else "OFFLINE_KNOWN_FLOW_REVIEW_ONLY",
      "reasons":tuple(sorted(set(reasons))),
      "all_live_udp_flows_certified":False,
      "physical_legacy_fencing_proven":False,
      "production_authorized":False,
      "router_commands":(),
    }
