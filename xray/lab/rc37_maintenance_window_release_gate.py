"""RC37 first-migration maintenance-window release review.

Distinct from RC36 seamless migration: an explicitly authorized outage may
allow TCP/UDP session loss, but NEVER waives safety of watchdog/cron fencing,
rollback, fail-closed routing, live process ownership or physical rescue.

All evidence here is caller-supplied and thus UNTRUSTED MODEL INPUT. Even
all-True values cannot authorize physical cutover. No shell/router commands.
"""
from dataclasses import dataclass, fields


@dataclass(frozen=True)
class MaintenanceEvidence:
    owner_approved_outage: bool = False
    owner_approved_existing_session_loss: bool = False
    fresh_live_config_binary_pid_start_ticks_boot_id: bool = False
    verified_independent_off_usb_rescue: bool = False
    exact_old_config_init_watchdog_backup: bool = False
    production_watchdog_s97_s98_s99_cron_descendants_fenced: bool = False
    no_global_killall_or_unscoped_signals: bool = False
    xray_api_enabled_candidate_tested_on_target_kernel: bool = False
    real_socks_and_tproxy_tcp_udp_ready: bool = False
    openai_eligibility_rechecked_with_fresh_ttl: bool = False
    dns_ipv6_and_default_route_fail_closed: bool = False
    durable_generation_cas_and_rollback_receipt: bool = False
    independent_local_recovery_and_operator_access: bool = False


def review(evidence=MaintenanceEvidence(), *, live_differs=True):
    if not isinstance(evidence, MaintenanceEvidence):
        raise TypeError("maintenance evidence must be typed")
    missing = tuple(
        "MISSING_" + f.name.upper()
        for f in fields(MaintenanceEvidence)
        if getattr(evidence, f.name) is not True
    )
    if not live_differs:
        decision = "SKIP_UNCHANGED"
        missing = ()
    elif missing:
        decision = "HARD_NO_GO_FIRST_MIGRATION"
    else:
        # These booleans are synthetic/caller assertions, NOT independent
        # kernel or physical proof. Do not convert this case to deployment.
        decision = "MODEL_READY_BUT_PHYSICAL_ATTESTATION_REQUIRED"
    return {
        "decision": decision,
        "missing": list(missing),
        "production_authorized": False,
        "router_commands": [],
        "live_cutover_executed": False,
        "model_evidence_is_physical_receipt": False,
        "session_continuity_guaranteed": False,
        "requires_separate_exact_execution_review": live_differs,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(review(), sort_keys=True))
