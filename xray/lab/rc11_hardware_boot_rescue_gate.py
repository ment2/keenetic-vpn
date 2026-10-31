"""RC11: independent boot/rescue *evidence contract*, NOT boot or deployment.

Extends the earlier separate mount-device gate with power-domain, boot-order,
root/sha, fsync crash and orphan refusal attestations. No I/O is performed.
Even synthetic all-true acceptance is REVIEW_ONLY and never production GO.
"""
from dataclasses import dataclass
from xray.lab.v30_outofusb_mount_gate import assess

@dataclass(frozen=True)
class RescueEvidence:
    mountinfo: str = ""
    independent_physical_power_domain_verified: bool = False
    persistence_observed_after_actual_cold_boot: bool = False
    rescue_mount_root_owned_0700: bool = False
    original_five_SHA256_verified: bool = False
    boot_guardian_executed_without_entware_usb: bool = False
    usb_physically_detached_when_restored: bool = False
    every_restore_file_fsync_confirmed: bool = False
    parent_directory_fsync_confirmed: bool = False
    journal_committed_before_activation: bool = False
    corrupted_journal_blocks_writes: bool = False
    corrupted_archive_blocks_writes: bool = False
    interrupted_rollback_replays_exact_bytes: bool = False
    guardian_boots_before_legacy_cron: bool = False
    no_unknown_descendant_before_activation: bool = False
    test_proven_on_actual_keenetic_ndm5: bool = False

def assess_rescue(e: RescueEvidence):
    mount=assess(e.mountinfo,observed_after_cold_boot=e.persistence_observed_after_actual_cold_boot,
                 root_owned_0700=e.rescue_mount_root_owned_0700,
                 independent_restore_after_usb_loss=e.usb_physically_detached_when_restored,
                 sha256_archive_verified=e.original_five_SHA256_verified,
                 guardian_exec_without_usb=e.boot_guardian_executed_without_entware_usb)
    required={
        "POWER_DOMAIN_UNVERIFIED":e.independent_physical_power_domain_verified,
        "BOOT_GUARDIAN_ORDER_UNVERIFIED":e.guardian_boots_before_legacy_cron,
        "UNKNOWN_DESCENDANT_MAY_RESTART":e.no_unknown_descendant_before_activation,
        "FILE_FSYNC_UNPROVEN":e.every_restore_file_fsync_confirmed,
        "DIRECTORY_FSYNC_UNPROVEN":e.parent_directory_fsync_confirmed,
        "JOURNAL_COMMIT_ORDER_UNPROVEN":e.journal_committed_before_activation,
        "CORRUPT_JOURNAL_CAN_WRITE":e.corrupted_journal_blocks_writes,
        "CORRUPT_SOURCE_CAN_WRITE":e.corrupted_archive_blocks_writes,
        "INTERRUPTED_ROLLBACK_NOT_REPLAYED":e.interrupted_rollback_replays_exact_bytes,
        "VENDOR_NDM5_NOT_PHYSICALLY_TESTED":e.test_proven_on_actual_keenetic_ndm5,
    }
    reasons=set(mount["reasons"])
    reasons.update(k for k,ok in required.items() if ok is not True)
    return {
        "state":"HARD_NO_GO" if reasons else "OFFLINE_REVIEW_CANDIDATE_ONLY",
        "reasons":sorted(reasons),
        "physical_router_certified":False,
        "deployment_authorized":False,
        "production_commands":[],
    }
