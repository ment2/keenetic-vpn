"""RC6 pinned source blobs, real runner cgroup-v1 blocker and boot-rescue NO-GO."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
RELEASE=ROOT/"xray/staging/v30-kernel49-rc6-offline-review.json"

class RC6ReleaseContract(unittest.TestCase):
    def setUp(self):
        self.data=json.loads(RELEASE.read_text(encoding="utf-8"))
    def test_exact_four_git_blob_pins(self):
        self.assertEqual(len(self.data["pinned_git_blobs"]),4)
        for path,digest in self.data["pinned_git_blobs"].items():
            with self.subTest(path=path):
                raw=(ROOT/path).read_bytes()
                self.assertEqual(hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest(),digest)
    def test_existing_rc5_remains_pinned(self):
        self.assertTrue((ROOT/self.data["paired_rc5"]).is_file())
    def test_real_cgroup1_was_blocked_not_claimed_pass(self):
        result=self.data["ci_real_cgroup_v1"]
        self.assertEqual(result["test_conclusion"],"BLOCKED_CGROUP_V1_MOUNT_UNAVAILABLE")
        self.assertFalse(result["real_cgroup_v1_fork_exec_tested"])
        self.assertEqual(result["run"],41216829749)
    def test_rehearsal_is_not_powerloss_or_hardware_rescue(self):
        result=self.data["host_posix_recovery"]
        self.assertEqual(self.data["ci_offline"]["tests"],481)
        self.assertTrue(result["fresh_host_sh_process_restores_all_five"])
        self.assertFalse(result["physical_usb_device_independent"])
        self.assertFalse(result["actual_router_cold_boot_proven"])
        self.assertFalse(result["physical_powerloss_fsync_proven"])
    def test_prod_authorization_denied(self):
        self.assertFalse(any(self.data["authorization"].values()))
        self.assertEqual(self.data["release_decision"],"HARD_NO_GO_PRODUCTION")
    def test_mips_proof_does_not_cover_new_cgroup(self):
        m=self.data["mips_last_proven"]
        self.assertEqual(m["run"],41215515431)
        self.assertFalse(m["new_rc6_cgroup_v1_proven"])
if __name__=="__main__":unittest.main()
