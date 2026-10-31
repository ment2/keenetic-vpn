"""RC4 exact Git blob pins, archived CI evidence and physical NO-GO."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
SPEC=ROOT/"xray/staging/v30-kernel49-rc4-rescue-review.json"

class ReviewRC4Tests(unittest.TestCase):
    def setUp(self):
        self.data=json.loads(SPEC.read_text())
    def test_exact_git_blob_immutable_sources(self):
        for path,digest in self.data["source_git_blob_sha1"].items():
            with self.subTest(path=path):
                blob=(ROOT/path).read_bytes()
                actual=hashlib.sha1(b"blob "+str(len(blob)).encode()+b"\0"+blob).hexdigest()
                self.assertEqual(actual,digest)
    def test_hardware_no_go(self):
        self.assertEqual(self.data["release_decision"],"HARD_NO_GO_PRODUCTION")
        self.assertFalse(self.data["production_cutover_authorized"])
        self.assertEqual(self.data["router_jobs_submitted"],0)
        self.assertEqual(self.data["production_commands"],[])
        self.assertTrue(all(v is False for v in self.data["safety_gates"].values()))
    def test_real_rescue_archive_not_bootable(self):
        self.assertEqual(self.data["review_archive_artifact_name"],
                         "v30-kernel49-offline-rescue-review-rc4")
        self.assertFalse(self.data["archive_is_bootable"])
        self.assertFalse(self.data["archive_contains_executable_agent"])
        self.assertFalse(self.data["hardware_boot_without_usb_proven"])
    def test_previous_rc3_contract_not_removed(self):
        self.assertTrue((ROOT/self.data["paired_prior"]).is_file())
        self.assertEqual(self.data["ci_unit_tests"],439)
        self.assertEqual(self.data["ci_conclusion"],"success")
        self.assertEqual(self.data["mips_last_proven"],"41213319142")
    def test_safety_constraints_in_generation_guard(self):
        constraints=self.data["design_constraints"]
        for phrase in ("guardian_cas_token_must_match_exact_owner_generation",
                       "no_automatic_uncertain_restart_replay",
                       "two_consecutive_inventory_scans_plus_sealed_scope_required",
                       "socket_inodes_and_detached_grandchildren_must_be_absent"):
            self.assertIn(phrase,constraints)

if __name__=="__main__":unittest.main()
