#!/usr/bin/env python3
"""Offline-only first migration readiness review. Never emits executable commands.

Required inputs are independently verified, non-secret evidence flags. This
does not probe or configure the router. A 'ready' status means only that an
exact, separate owner approval can be requested; it is NEVER a deployment grant.
"""
from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class Evidence:
    live_pid_and_ticks: bool = False
    live_config_and_binary_hashes: bool = False
    backup_restorable_locally: bool = False
    local_out_of_band_access: bool = False
    api_candidate_config_valid: bool = False
    both_ingress_protocols_exclusive_handoff_proven: bool = False
    udp_end_to_end_proven: bool = False
    tcp_drain_proven: bool = False
    tproxy_fwmark_table100_kernel_proven: bool = False
    dns_ipv6_leak_tests_passed: bool = False
    watchdog_pid_scoped_and_fenced: bool = False
    no_global_killall_on_any_active_path: bool = False
    kernel_killswitch_remains_fail_closed: bool = False
    no_direct_provider_fallback: bool = False
    candidate_vpn_qualified: bool = False
    rollback_both_protocols_tested: bool = False
    controller_journal_reboot_recovery_tested: bool = False
    source_snapshot_current: bool = False
    acceptable_outage_confirmed: bool = False


def assess(evidence: Evidence) -> dict:
    missing = [k for k, v in asdict(evidence).items() if v is not True]
    # Even fully passing synthetic evidence cannot authorize deploy.
    return {
        "decision": "BLOCKED" if missing else "READY_FOR_SEPARATE_OWNER_APPROVAL",
        "missing_gates": missing,
        "production_commands": [],
        "deploy_authorized": False,
        "is_real_router_evidence": False,
        "warning": "Offline flags are assertions; independent live evidence is required."
    }
