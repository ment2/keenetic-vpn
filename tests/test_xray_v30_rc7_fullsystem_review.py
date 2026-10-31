"""RC7 full-system guest source pins and NO-GO release evidence."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
RELEASE=ROOT/"xray/staging/v30-rc7-fullsystem-review.json"
class FullSystemRC7Gate(unittest.TestCase):
    def setUp(self):
        self.d=json.loads(RELEASE.read_text(encoding="utf-8"))
    def test_exact_five_git_blobs(self):
        self.assertEqual(len(self.d["source_git_blobs"]),5)
        for path,sha in self.d["source_git_blobs"].items():
            with self.subTest(path=path):
                b=(ROOT/path).read_bytes()
                self.assertEqual(hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest(),sha)
    def test_fullsystem_not_user_mode(self):
        vm=self.d["fullsystem"]
        self.assertEqual(vm["kernel"],"6.8.0-147-generic")
        self.assertEqual(vm["arch"],"x86_64")
        self.assertIn("full-system",vm["acceleration"])
        self.assertEqual(vm["run_id"],41218961516)
        self.assertEqual(vm["conclusion"],"success")
    def test_privileged_escape_is_no_go_even_when_cgroup_tests_pass(self):
        vm=self.d["fullsystem"]
        self.assertTrue(vm["real_cgroup_v1_pids_mounted"])
        self.assertTrue(vm["real_fork_exec_inheritance"])
        self.assertTrue(vm["privileged_descendant_escaped_cgroup_v1"])
        self.assertFalse(vm["scope_is_secure"])
        self.assertFalse(vm["actual_mips_kernel49_proven"])
        self.assertFalse(vm["cas_generation_claim_inside_vm"])
        self.assertEqual(vm["guardian_flock_rounds"]*vm["guardians_per_round"],16)
    def test_virtual_disks_are_not_physical_rescue(self):
        r=self.d["rescue"]
        self.assertEqual(r["separate_virtual_ext4_disks"],2)
        self.assertTrue(r["guest_fdatasync_file_and_fsync_directory"])
        self.assertTrue(r["host_forced_qemu_sigkill_after_two_files"])
        self.assertTrue(r["recovered_journal_stage_2"])
        self.assertEqual(r["restored_originals"],5)
        for s in ("physical_device_independence_proven",
                  "actual_hardware_powerloss_proven",
                  "actual_physical_usb_removal_proven"):
            self.assertFalse(r[s])
    def test_no_prod_and_prior_rc6(self):
        self.assertTrue((ROOT/self.d["paired_rc6"]).exists())
        self.assertFalse(any(self.d["authorization"].values()))
        self.assertEqual(self.d["release_decision"],"HARD_NO_GO_PRODUCTION")
        self.assertTrue(self.d["source_artifacts_only"])
    def test_static_source_never_routes_to_prod(self):
        vm=(ROOT/"xray/lab/rc7_fullvm_runner.sh").read_text()
        self.assertIn("RUNNER_TEMP",vm)
        self.assertIn("qemu-system-x86_64",vm)
        self.assertIn("kill -KILL",vm)
        self.assertIn("rc7_stage=second",vm)
        self.assertNotIn("ssh root@",vm)
        self.assertNotIn("/opt/etc/init.d/",vm)
        self.assertIn("GUEST_REAL_CGROUP1_FORK_EXEC_SOCKET_INODE",vm)
    def test_guest_fdatasync_fsync_checkpoints_present(self):
        c=(ROOT/"xray/lab/rc7_guest_fdatasync.c").read_text()
        for check in ("fdatasync(fd)","fsync(parent)","/mnt/active/"):
            self.assertIn(check,c)
        init=(ROOT/"xray/lab/rc7_fullvm_init").read_text()
        self.assertEqual(init.count("/bin/rc7fsync "),3)
if __name__=="__main__":unittest.main()
