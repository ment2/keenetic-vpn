"""RC39 offline review of a Home Assistant off-USB rescue receipt.

A success means only that supplied claims are internally consistent.
Neither a green offline test nor a remote file's existence proves recovery
when Keenetic USB storage fails. This module NEVER transfers configuration,
reads credentials, connects to Home Assistant or deploys anything.
"""
from dataclasses import dataclass
import re

SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class OffsiteReceipt:
    source_archive_sha256: str = ""
    remote_archive_sha256: str = ""
    host_key_verified_out_of_band: bool = False
    ssh_authenticated: bool = False
    isolated_storage_from_router_usb: bool = False
    remote_file_owner_only: bool = False
    encryption_at_rest_verified: bool = False
    backup_contents_manifest_verified: bool = False
    physical_restore_test_completed: bool = False
    local_operator_recovery_available: bool = False


def review(receipt=OffsiteReceipt()):
    if not isinstance(receipt, OffsiteReceipt):
        raise TypeError("typed receipt required")
    missing = []
    for name in (
        "host_key_verified_out_of_band",
        "ssh_authenticated",
        "isolated_storage_from_router_usb",
        "remote_file_owner_only",
        "encryption_at_rest_verified",
        "backup_contents_manifest_verified",
        "physical_restore_test_completed",
        "local_operator_recovery_available",
    ):
        if getattr(receipt, name) is not True:
            missing.append("MISSING_" + name.upper())
    digest_ok = bool(SHA256.fullmatch(receipt.source_archive_sha256))
    digest_ok &= bool(SHA256.fullmatch(receipt.remote_archive_sha256))
    digest_ok &= receipt.source_archive_sha256 == receipt.remote_archive_sha256
    if not digest_ok:
        missing.append("ARCHIVE_SHA256_NOT_END_TO_END_VERIFIED")
    return {
        "decision": "OFFSITE_RECEIPT_INCOMPLETE" if missing else "CLAIMED_RECEIPT_REQUIRES_INDEPENDENT_AUDIT",
        "missing": sorted(missing),
        "bytes_transferred_by_gate": 0,
        "physical_recovery_proven_by_gate": False,
        "production_cutover_authorized": False,
        "router_commands": [],
    }


if __name__ == "__main__":
    import json
    print(json.dumps(review(), sort_keys=True))
