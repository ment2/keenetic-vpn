"""Versioned original rollback data must equal frozen RC1 release sources."""
import json
import hashlib
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
RESCUE=ROOT/"xray/staging/v30-rescue-contract-v1.json"
RELEASE=ROOT/"xray/staging/v30-release-manifest-v1.json"


class RescueManifestContract(unittest.TestCase):
    def setUp(self):
        self.spec=json.loads(RESCUE.read_text())
        self.release=json.loads(RELEASE.read_text())

    def test_exact_archived_five_files(self):
        self.assertEqual(self.spec["paired_release"],self.release["release"])
        wanted={e["role"]:e for e in self.release["entries"] if "legacy_snapshot_path" in e}
        self.assertEqual(set(wanted),{e["role"] for e in self.spec["rollback_files"]})
        self.assertEqual(len(wanted),5)
        for line in self.spec["rollback_files"]:
            with self.subTest(role=line["role"]):
                old=wanted[line["role"]]
                self.assertEqual(line["restore_source"],old["legacy_snapshot_path"])
                data=(ROOT/line["restore_source"]).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(),line["restore_sha256"])
                self.assertEqual(line["restore_sha256"],old["legacy_snapshot_sha256"])
                self.assertEqual(line["staging_sha256"],old["staging_sha256"])
                self.assertEqual(line["restore_mode"],"0755")
                self.assertEqual(line["source_snapshot_git_mode"],"100755")

    def test_rollback_package_does_not_authorize_live_deploy(self):
        self.assertFalse(self.spec["installation_permitted"])
        self.assertFalse(self.spec["automatic_restoration_permitted"])
        self.assertFalse(self.spec["physical_non_usb_rescue_verified"])
        self.assertEqual(self.spec["production_commands"],[])
        self.assertEqual(self.spec["artifact_type"],"REVIEW_ONLY_VERSIONED_ROLLBACK_SPEC")

    def test_backup_absent_or_corrupt_refuses_writes(self):
        invariants=self.spec["restore_invariants"]
        self.assertIn("preverify_all_5_SHA256_before_any_writes",invariants)
        self.assertIn("fail_closed_if_archive_missing_corrupt",invariants)
        self.assertIn("never_unblock_network_on_failed_restore",invariants)

    def test_kernel_and_out_of_usb_boot_gate_persist(self):
        gates=self.spec["required_host_evidence"]
        self.assertIn("kernel_4_9_safe_supervision_design",gates)
        self.assertIn("physical_rescue_mount_independent_of_entware_usb",gates)
        self.assertIn("rescue_executable_from_boot_without_usb",gates)

    def test_no_unexpected_rollback_path(self):
        for entry in self.spec["rollback_files"]:
            self.assertTrue(entry["restore_source"].startswith("xray/production/opt/"))
            self.assertFalse(".." in entry["restore_source"])


if __name__=="__main__":
    unittest.main()
