"""Offline review-only deterministic rescue archive and tamper-denial tests."""
import copy
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

from xray.lab import v30_review_rescue_bundle as r

class RescueBundleTests(unittest.TestCase):
    def test_archive_is_byte_for_byte_deterministic(self):
        a=r.fixed_tar(r.file_set())
        b=r.fixed_tar(r.file_set())
        self.assertEqual(a,b)
        self.assertGreater(len(a),100)
    def test_five_archived_sources_and_safe_permissions(self):
        data=r.fixed_tar(r.file_set())
        with tarfile.open(fileobj=io.BytesIO(data),mode="r:") as tf:
            members=tf.getmembers()
            self.assertEqual(len(members),6)
            self.assertTrue(all(m.isfile() and m.mode==0o600 for m in members))
            self.assertFalse(any(m.issym() or m.islnk() for m in members))
    def test_real_review_archive_verified_no_prod(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/r.ARCHIVE
            path.write_bytes(r.fixed_tar(r.file_set()))
            result=r.inspect(path)
            self.assertEqual(result["status"],"PASS_REVIEW_ONLY_ARCHIVE")
            self.assertEqual(result["originals"],5)
            self.assertFalse(result["physical_rescue_proven"])
            self.assertFalse(result["production_authorized"])
    def test_corrupted_archive_detected(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/r.ARCHIVE
            bundle=bytearray(r.fixed_tar(r.file_set()))
            pos=bundle.find(b"rescue-metadata.json")
            self.assertGreater(pos,0)
            bundle[pos:pos+4]=b"xxxx"
            path.write_bytes(bundle)
            with self.assertRaises(ValueError):
                r.inspect(path)
    def test_tampered_archive_content_detected_even_if_metadata_self_consistent(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/r.ARCHIVE
            entries=r.file_set()
            item=next(x for x in entries if x.startswith("originals/"))
            entries[item]+=b"\n# NOT ORIGINAL\n"
            path.write_bytes(r.fixed_tar(entries))
            with self.assertRaises(ValueError):
                r.inspect(path)
    def test_bundle_metadata_cannot_authorize_physical_restore(self):
        obj=json.loads(r.file_set()[r.METADATA])
        self.assertEqual(obj["status"],"OFFLINE_REVIEW_ONLY_NOT_BOOTABLE")
        for key in ("authorizes_production_restore","contains_executable_recovery_agent",
                    "stored_outside_entware_usb_on_real_keenetic",
                    "tested_after_physical_power_loss","actual_mount_identity_verified"):
            self.assertIs(obj[key],False)
        self.assertEqual(obj["router_commands"],[])
    def test_no_installable_script_or_unsafe_target(self):
        for name in r.file_set():
            self.assertNotIn("..",name)
            self.assertFalse(name.startswith("/opt"))
    def test_output_rejects_prod_target(self):
        with self.assertRaises(ValueError):r.output_path("/opt/etc/init.d/S97xray")

if __name__=="__main__":unittest.main()
