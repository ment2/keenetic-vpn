"""RC23 offline *evidence* gate for original outbound destination and host UDP return.

No packets, no router, no privileges. All booleans synthetic, and even all-true
never authorizes hardware or production cutover.
"""
from dataclasses import dataclass, fields
import ipaddress

@dataclass(frozen=True)
class Witness:
    guest_is_disposable_mips49: bool = False
    exact_kernel_modules_and_xray_hash: bool = False
    tproxy_ingress_tcp_udp_packet_counter_positive: bool = False
    tcp_and_udp_original_destination_observed: bool = False
    no_freedom_redirect_or_destination_rewriting: bool = False
    independent_backend_network_stack_verified: bool = False
    xray_outbound_tcp_dial_exact_original_destination: bool = False
    xray_outbound_udp_dial_exact_original_destination: bool = False
    backend_tcp_payload_exact: bool = False
    backend_udp_payload_exact: bool = False
    host_udp_return_payload_exact: bool = False
    independent_udp_hostfwd_positive_control: bool = False
    no_direct_fallback_after_xray_death: bool = False
    no_ipv6_dns_leak: bool = False
    origin: str = ""
    tcp_outbound: str = ""
    udp_outbound: str = ""
    backend_tcp: str = ""
    backend_udp: str = ""

def _endpoint(value):
    try:
        host,sep,port = value.rpartition(":")
        if not sep: return None
        ipaddress.ip_address(host)
        n=int(port)
        if n<1 or n>65535: return None
        return host,n
    except ValueError:
        return None

def evaluate(w: Witness):
    failed=[]
    for f in fields(Witness):
        if f.type is bool and getattr(w,f.name) is not True:
            failed.append("UNPROVEN:"+f.name)
    dest=_endpoint(w.origin)
    if dest is None:
        failed.append("ORIGINAL_DESTINATION_INVALID")
    for name in ("tcp_outbound","udp_outbound","backend_tcp","backend_udp"):
        actual=_endpoint(getattr(w,name))
        if actual is None or actual!=dest:
            failed.append("ORIGINAL_DEST_NOT_PRESERVED:"+name)
    return {
        "decision":"HARD_NO_GO" if failed else "OFFLINE_REVIEW_CANDIDATE_ONLY",
        "reasons":tuple(sorted(set(failed))),
        "original_destination_proven":False,
        "host_bidirectional_udp_proven":False,
        "production_authorized":False,
        "router_commands":(),
    }

def synthetic_all_true():
    kw={f.name:True for f in fields(Witness) if f.type is bool}
    e="10.0.2.15:19191"
    return Witness(**kw,origin=e,tcp_outbound=e,udp_outbound=e,backend_tcp=e,backend_udp=e)
