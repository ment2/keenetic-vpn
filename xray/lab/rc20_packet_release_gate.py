"""RC20 fail-closed proof gate. Never executes router commands or authorizes cutover.

Observations are independent; QEMU module/rule installation is not Xray forwarding.
All-synthetic-true only means OFFLINE_REVIEW, not router/hardware certification.
"""
from dataclasses import dataclass, fields

@dataclass(frozen=True)
class Witness:
    exact_mips49_kernel_and_modules_sha: bool=False
    guest_pcnet_ethernet_packet_ingress: bool=False
    guest_xt_tproxy_tcp_rule_counter_positive: bool=False
    guest_xt_tproxy_udp_rule_counter_positive: bool=False
    tcp_payload_equal_after_tproxy: bool=False
    udp_payload_equal_after_tproxy: bool=False
    tcp_client_received_same_payload: bool=False
    udp_client_received_same_payload: bool=False
    real_xray_mips_inbound_tcp_observed: bool=False
    real_xray_mips_inbound_udp_observed: bool=False
    xray_uid_caps_only_raw_and_pr_get_no_new_privs: bool=False
    xray_pid_startticks_guardian_generation_cas_verified: bool=False
    stale_generation_and_pid_reuse_prevented: bool=False
    process_death_no_tcp_udp_direct_fallback: bool=False
    ipv6_and_dns_no_leak: bool=False
    legacy_7_spawners_preboot_inhibited_and_exact_sha_attested: bool=False
    privileged_root_cgroup_v1_escape_independently_fenced: bool=False
    unknown_orphan_and_socket_inode_scan_complete: bool=False
    usb_absent_physical_cold_boot_rescue_independent_power_domain: bool=False
    five_originals_exact_sha_and_crash_fsync_rollback_on_hardware: bool=False
    vendor_keenetic_ndm5_mips_kernel_compatibility_verified: bool=False

def evaluate(w: Witness):
    failed=tuple(f.name for f in fields(Witness) if getattr(w,f.name) is not True)
    return {
        "state":"HARD_NO_GO" if failed else "OFFLINE_REVIEW_CANDIDATE_ONLY",
        "reasons":list(failed),
        "tcp_udp_packet_path_proven":False, # offline booleans are not packet artifacts
        "production_authorized":False,
        "router_commands":[],
        "hardware_certified":False,
    }
