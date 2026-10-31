"""Versioned Linux49 shared-flock boot/rescue contract, not live authorization."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
SPEC=ROOT/"xray/staging/v30-kernel49-cooperative-boot-rescue-v1.json"


class Kernel49RescueGateTests(unittest.TestCase):
    def setUp(self):
        self.data=json.loads(SPEC.read_text())

    def test_all_exact_nine_git_blobs_pinned(self):
        self.assertEqual(len(self.data["git_blob_sha1"]),9)
        for path,expected in self.data["git_blob_sha1"].items():
            with self.subTest(path=path):
                raw=(ROOT/path).read_bytes()
                actual=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
                self.assertEqual(actual,expected)

    def test_non_usb_physical_recovery_not_fabricated(self):
        for key,passed in self.data["boot_rescue_gates"].items():
            with self.subTest(key=key):
                self.assertIs(passed,False)
        self.assertFalse(self.data["automatic_reboot_recovery_authorized"])
        self.assertFalse(self.data["production_authorized"])
        self.assertFalse(self.data["install_authorized"])
        self.assertFalse(self.data["merge_authorized"])
        self.assertFalse(self.data["production_deployment"])
        self.assertEqual(self.data["status"],"LAB_ONLY_NOT_DEPLOYABLE")
        self.assertEqual(self.data["router_commands"],[])

    def test_no_live_usb_boot_or_kernel49_proof_in_ci(self):
        self.assertFalse(self.data["lab_evidence"]["physical_router_proven"])
        self.assertIn("old_child_or_listener_alive",self.data["blocked_scenarios"])
        self.assertIn("unknown_detached_descendant",self.data["blocked_scenarios"])
        self.assertIn("inflight_UNCERTAIN_without_review",self.data["blocked_scenarios"])

    def test_versioned_links_to_unmodified_rc1_rc2(self):
        for key in ("paired_rc1_release","paired_rc1_rescue","paired_rc2_parent_owned"):
            with self.subTest(key=key):
                self.assertTrue((ROOT/self.data[key]).is_file())
        self.assertEqual(self.data["common_mutex"],
                         "/opt/var/run/xray-v30-supervisor.lock")
        self.assertEqual(set(self.data["entrypoint_roles"]),
                         {"S97","S98","S99","watchdog","cron"})

    def test_only_lab_paths_in_release_manifest(self):
        for p in self.data["git_blob_sha1"]:
            self.assertTrue(p.startswith(("xray/lab/","xray/staging/")))
            self.assertNotIn("production/opt",p)
        self.assertEqual(len([p for p in self.data["git_blob_sha1"]
            if "/v30_kernel49_entrypoints/" in p]),6)


if __name__=="__main__":
    unittest.main()
