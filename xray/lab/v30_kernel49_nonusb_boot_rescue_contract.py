#!/usr/bin/env python3
"""Review-only exact boot-rescue acceptance state machine for Keenetic.

A GitHub tar artifact cannot boot a router. This module models candidate
rescue content layout, physical-independent mount claims, and failure
injections as OFFLINE TEST DATA. Never writes /opt, mounts devices, starts
Xray, or invokes router jobs. Any hardware field unverified is NO-GO.
"""
from dataclasses import dataclass, fields
import hashlib
import json
from pathlib import Path

class RescueBlocked(RuntimeError):
    pass

LAYOUT = {
  "manifest":"rescue-v30/manifest.json",
  "original_scripts":"rescue-v30/originals/*.sh",
  "guardian":"rescue-v30/bin/guardian",
  "guardian_config":"rescue-v30/etc/guardian.json",
  "boot_hook":"rescue-v30/boot/boot-hook",
  "log":"rescue-v30/var/recovery.log",
}
BLOCKED = ("NO_RESCUE_BYTES","BAD_RESCUE_SHA","SAME_USB_MOUNT",
           "MISSING_EXECUTABLE_GUARDIAN","BOOT_HOOK_NOT_PROVEN",
           "CORRUPT_OR_UNFSYNCED_JOURNAL","FOREIGN_DESCENDANT_LIVE")

@dataclass(frozen=True)
class Evidence:
    original_rc1_sha256_verified: bool=False
    guardian_binary_exact_sha256_verified: bool=False
    guardian_works_without_python_entware: bool=False
    guardian_was_audited_for_kernel49: bool=False
    physically_separate_non_usb_device: bool=False
    distinct_kernel_device_and_mount_id: bool=False
    fsync_and_readback_verified: bool=False
    physical_power_loss_rehearsal_verified: bool=False
    boot_hook_runs_before_xray_services: bool=False
    boot_hook_executable_without_entware: bool=False
    kernel49_process_containment_verified: bool=False
    all_legacy_restart_writers_fenced: bool=False
    kill_switch_remains_closed_on_failure: bool=False
    all_5_original_files_complete: bool=False
    durable_journal_integrity_verified: bool=False

@dataclass(frozen=True)
class Fault:
    missing_usb: bool=False
    backup_missing: bool=False
    archive_corrupt: bool=False
    rescue_same_device: bool=False
    guardian_not_executable: bool=False
    power_loss_before_journal_fsync: bool=False
    power_loss_during_script_restore: bool=False
    old_descendant_alive: bool=False
    boot_hook_missing: bool=False

def acceptance(evidence=Evidence(),fault=Fault(),*,offline=True):
    reasons=["MISSING_"+f.name.upper()
             for f in fields(Evidence) if getattr(evidence,f.name) is not True]
    if fault.archive_corrupt:reasons.append("BAD_RESCUE_SHA")
    if fault.backup_missing:reasons.append("NO_RESCUE_BYTES")
    if fault.rescue_same_device:reasons.append("SAME_USB_MOUNT")
    if fault.guardian_not_executable:reasons.append("MISSING_EXECUTABLE_GUARDIAN")
    if fault.boot_hook_missing:reasons.append("BOOT_HOOK_NOT_PROVEN")
    if fault.power_loss_before_journal_fsync or fault.power_loss_during_script_restore:
        reasons.append("CORRUPT_OR_UNFSYNCED_JOURNAL")
    if fault.old_descendant_alive:reasons.append("FOREIGN_DESCENDANT_LIVE")
    # A rescue genuinely outside USB may still work without USB, but
    # that physical property must be independently proven. Never infer
    # this from a synthetic success or GitHub archive location.
    if fault.missing_usb and not evidence.guardian_works_without_python_entware:
        reasons.append("USB_ABSENCE_NO_GUARDIAN")
    if offline is not True:
        raise RescueBlocked("live router evaluation not implemented")
    return {
      "decision":"HARD_NO_GO" if reasons else "SYNTHETIC_CONTRACT_SATISFIED_ONLY",
      "reasons":sorted(set(reasons)),
      "physical_boot_proven":False,
      "automatic_restore_authorized":False,
      "production_commands":[],
      "layout":LAYOUT,
      "scope":"OFFLINE_REVIEW_NO_INSTALL",
    }

def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--offline-plan",action="store_true")
    a=p.parse_args()
    if not a.offline_plan:p.error("only --offline-plan")
    print(json.dumps(acceptance(),sort_keys=True))

if __name__=="__main__":main()
