import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from xray.lab.rc38_rescue_archive_audit import audit_bundle, RescueAuditError


class RescueAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        path = self.root / "opt" / "etc" / "init.d" / "S97xray"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"test-only archival bytes\n")
        os.chmod(path, 0o600)
        self.data = b"test-only archival bytes\n"
        self.entry = {
            "path": "/opt/etc/init.d/S97xray",
            "sha256": hashlib.sha256(self.data).hexdigest(),
            "size": len(self.data),
            "original_mode": "0o755",
        }
        self.write_manifest()

    def write_manifest(self, entries=None):
        (self.root / "manifest.json").write_text(json.dumps({
            "entries": [self.entry] if entries is None else entries
        }))

    def test_archived_permissions_differ_but_bytes_valid(self):
        outcome = audit_bundle(self.root)
        self.assertEqual(outcome["status"], "ARCHIVE_VALID_READ_ONLY")
        self.assertEqual(outcome["permission_restore_required"], 1)
        self.assertFalse(outcome["off_usb_rescue_proven"])
        self.assertFalse(outcome["production_authorized"])
        self.assertEqual(outcome["router_actions"], [])

    def test_missing_file_rejected(self):
        (self.root / "opt/etc/init.d/S97xray").unlink()
        outcome = audit_bundle(self.root)
        self.assertEqual(outcome["status"], "ARCHIVE_INVALID")
        self.assertEqual(outcome["issues"], ["MISSING_ENTRY_0"])

    def test_corrupted_sha_rejected(self):
        (self.root / "opt/etc/init.d/S97xray").write_bytes(b"corrupt payload\n")
        outcome = audit_bundle(self.root)
        self.assertIn("SIZE_MISMATCH_0", outcome["issues"])

    def test_equal_size_wrong_digest_rejected(self):
        (self.root / "opt/etc/init.d/S97xray").write_bytes(b"X" * len(self.data))
        outcome = audit_bundle(self.root)
        self.assertEqual(outcome["issues"], ["HASH_MISMATCH_0"])

    def test_symlink_rejected_even_if_inside_archive(self):
        source = self.root / "opt/etc/init.d/S97xray"
        source.unlink()
        source.symlink_to(self.root / "manifest.json")
        with self.assertRaisesRegex(RescueAuditError, "symlink"):
            audit_bundle(self.root)

    def test_traversal_rejected(self):
        bad = dict(self.entry, path="/opt/../../etc/passwd")
        self.write_manifest([bad])
        with self.assertRaisesRegex(RescueAuditError, "traversal"):
            audit_bundle(self.root)

    def test_duplicate_rejected(self):
        self.write_manifest([self.entry, self.entry])
        with self.assertRaisesRegex(RescueAuditError, "duplicate"):
            audit_bundle(self.root)

    def test_bad_mode_rejected(self):
        self.write_manifest([dict(self.entry, original_mode="0o1777")])
        with self.assertRaisesRegex(RescueAuditError, "original_mode"):
            audit_bundle(self.root)

    def test_missing_manifest_rejected(self):
        (self.root / "manifest.json").unlink()
        with self.assertRaises(RescueAuditError):
            audit_bundle(self.root)

    def test_empty_manifest_rejected(self):
        self.write_manifest([])
        with self.assertRaises(RescueAuditError):
            audit_bundle(self.root)


if __name__ == "__main__":
    unittest.main()
