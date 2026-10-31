"""RC5 exact source refs, MIPS generation-CAS evidence and boot NO-GO."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
PLAN=ROOT/"xray/staging/v30-kernel49-rc5-boot-rescue-review.json"

class RC5Acceptance(unittest.TestCase):
    def setUp(self):
        self.data=json.loads(PLAN.read_text(encoding="utf-8"))
    def test_three_exact_git_blob_pins(self):
        self.assertEqual(len(self.data["source_contract_blobs"]),3)
        for source,expected in self.data["source_contract_blobs"].items():
            with self.subTest(source=source):
                raw=(ROOT/source).read_bytes()
                actual=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
                self.assertEqual(actual,expected)
    def test_prior_release_rollback_refs_remain(self):
        self.assertTrue((ROOT/self.data["prior_release_manifest"]).is_file())
        self.assertTrue((ROOT/self.data["prior_originals_manifest"]).is_file())
    def test_mips_and_offline_proof_bounded(self):
        self.assertEqual(self.data["offline_ci"]["tests"],464)
        self.assertEqual(self.data["mips_ci"]["guardian_claimants_first"],8)
        self.assertEqual(self.data["mips_ci"]["guardian_claimants_second"],8)
        self.assertFalse(self.data["mips_ci"]["kernel_tproxy_proven"])
        self.assertIn("SOCKS5_UDP_ASSOCIATE",self.data["mips_ci"]["transports"])
    def test_guardian_layout_never_embeds_existing_real_mount(self):
        layout=self.data["physical_candidate_layout"]
        self.assertEqual(layout["nonusb_device"],"EXACT_PHYSICAL_DEVICE_NOT_SELECTED")
        self.assertFalse(layout["boot_hook_writes_authorized"])
        self.assertEqual(layout["required_guardian_runtime"],
                         "independent executable (not Entware/Python on USB)")
        self.assertIn("before any router Xray",layout["required_boot_order"])
    def test_no_hardware_gate_fabricated(self):
        self.assertFalse(any(self.data["hardware_gates"].values()))
        self.assertEqual(self.data["release_decision"],"HARD_NO_GO_PRODUCTION")
        self.assertFalse(self.data["authorization"]["prod_deploy"])
        self.assertFalse(self.data["authorization"]["automatic_restore"])
        self.assertEqual(self.data["authorization"]["router_jobs"],0)
    def test_all_faults_included(self):
        faults=set(self.data["faults_tested_in_offline_model"])
        for x in ("usb_missing","backup_missing","same_device_alias",
                  "journal_fsync_interrupted","untracked_orphan_listener",
                  "script_restore_interrupted"):
            self.assertIn(x,faults)
if __name__=="__main__":unittest.main()
