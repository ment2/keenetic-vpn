"""RC8 immutable staged proof. QEMU success does not authorize router changes."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
RELEASE=ROOT/"xray/staging/v30-rc8-privdrop-failclosed-review.json"
class RC8ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.d=json.loads(RELEASE.read_text())
    def test_git_blob_pins_are_exact(self):
        self.assertEqual(len(self.d["source_git_blobs"]),4)
        for path,digest in self.d["source_git_blobs"].items():
            with self.subTest(path=path):
                raw=(ROOT/path).read_bytes()
                got=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
                self.assertEqual(got,digest)
    def test_pre_exec_privilege_drop_explicit(self):
        source=(ROOT/"xray/lab/rc8_guest_privdrop.c").read_text()
        self.assertIn('drop();execl("/bin/rc8privdrop","rc8privdrop","worker"',source)
        self.assertIn('drop();execl("/bin/rc8privdrop","rc8privdrop","orphan"',source)
        self.assertIn("PR_SET_NO_NEW_PRIVS",source)
        self.assertIn("setresuid(65534,65534,65534)",source)
        self.assertIn("setresgid(65534,65534,65534)",source)
        self.assertIn("GUARDIAN_DENIES_RESTART_UNKNOWN_REPARENTED_DESCENDANT",source)
    def test_three_full_vm_scenarios_and_real_bad_byte_verification(self):
        r=self.d["verified_fullsystem"]
        self.assertEqual(r["ci_conclusion"],"success")
        self.assertEqual(r["ci_run"],41220515203)
        self.assertEqual(r["scenarios"],["baseline","journal-corrupt","rescue-corrupt"])
        self.assertTrue(r["corrupted_bytes_read_back_and_confirmed"])
        self.assertTrue(r["fsck_replayed_virtual_ext4_journal_before_damage_injection"])
        self.assertTrue(r["journal_corruption_blocks_any_active_file_write"])
        self.assertTrue(r["rescue_corruption_blocks_any_active_file_write"])
        self.assertEqual(r["baseline_originals_restored"],5)
    def test_risky_privileged_legacy_and_physical_boot_are_no_go(self):
        r=self.d["verified_fullsystem"]
        self.assertTrue(r["privileged_cgroup_v1_escape_still_possible"])
        for key in ("scope_is_sealed_against_all_legacy_privileged_processes",
                    "real_socks_xray_process_in_vm","guardian_production_cas_in_vm",
                    "independent_physical_storage_proven","physical_powerloss_verified",
                    "keenetic_linux_4_9_tested"):
            self.assertFalse(r[key])
        self.assertEqual(self.d["release_decision"],"HARD_NO_GO_PRODUCTION")
        self.assertFalse(any(self.d["restrictions"].values()))
    def test_prior_rc7_preserved(self):
        self.assertTrue((ROOT/self.d["prior_rc7"]).is_file())
    def test_runner_requires_fail_closed_without_silent_replay(self):
        s=(ROOT/"xray/lab/rc8_fullvm_runner.sh").read_text()
        for val in ("RC8_SCENARIO","journal-corrupt","rescue-corrupt","e2fsck -fy",
                    "cmp", "FAIL_CLOSED_CORRUPT_JOURNAL_NO_RESTORATION",
                    "FAIL_CLOSED_CORRUPT_RESCUE_NO_RESTORATION",
                    "DANGEROUS_SECOND_BOOT_WROTE_ACTIVE_FILE"):
            self.assertIn(val,s)
        self.assertIn("RC8: HARD_NO_GO_PHYSICAL_KEENETIC_RUNTIME_CGROUP_BOOT_USB_TPROXY",s)
        self.assertNotIn("ssh root@",s)
        self.assertNotIn("/opt/etc/init.d/",s)

if __name__=="__main__":
    unittest.main()
