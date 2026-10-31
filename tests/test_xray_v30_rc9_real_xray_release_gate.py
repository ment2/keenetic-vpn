"""RC9: immutable full-system real Xray capability proof is not router authority."""
import hashlib
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
M=ROOT/"xray/staging/v30-rc9-real-xray-capability-review.json"
class RC9RealXrayGate(unittest.TestCase):
    def setUp(self):
        self.m=json.loads(M.read_text())
    def test_pin_all_six_git_blobs(self):
        self.assertEqual(len(self.m["source_blobs"]),6)
        for path,expected in self.m["source_blobs"].items():
            with self.subTest(path=path):
                data=(ROOT/path).read_bytes()
                digest=hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
                self.assertEqual(digest,expected)
    def test_xray_binary_sha_not_unverified_release_fetch(self):
        binary=self.m["official_xray_binary"]
        self.assertEqual(binary["version"],"26.2.6")
        self.assertEqual(binary["architecture"],"linux/amd64")
        self.assertEqual(binary["archive_sha256"],
          "29ce535b56e207a406ffa1c2d4842dcc410be003eff8ec508bb732abc9f8e385")
        self.assertEqual(binary["executable_sha256"],
          "3f650abf1fc4a4fbf5abe7fc9990a2658020907cd984214e9c075b4b00989fea")
        self.assertTrue(binary["hash_verified_by_ci"])
    def test_real_caps_and_executable_not_kernel49(self):
        c=self.m["confirmed_guest"]
        self.assertTrue(c["zero_caps_rejected_ip_transparent_tcp"])
        self.assertTrue(c["zero_caps_rejected_ip_transparent_udp"])
        self.assertTrue(c["only_cap_net_raw_success_tcp"])
        self.assertTrue(c["only_cap_net_raw_success_udp"])
        self.assertTrue(c["real_xray_tproxy_inbound_listener"])
        self.assertTrue(c["no_new_privs_before_exec"])
        self.assertEqual(c["only_cap_net_raw_effective_hex"],"0000000000002000")
        self.assertTrue(c["native_kernel_tproxy_packet_redirection_not_tested_in_rc9"])
        self.assertTrue(c["real_mips_linux49_kernel_not_proven"])
        self.assertTrue(c["legacy_privileged_processes_not_fenced"])
    def test_parent_process_identity_and_direct_child_death(self):
        g=self.m["confirmed_guest"]
        self.assertTrue(g["child_pid_start_ticks_pinned"])
        self.assertTrue(g["crashed_parent_dies_by_sigkill"])
        self.assertTrue(g["pdeathsig_real_xray_child_listener_closed"])
        self.assertFalse(g["guardian_sends_signal_to_unknown_pid"])
        source=(ROOT/"xray/lab/rc9_guest_parent_crash.c").read_text()
        self.assertIn("RC9_OWNER: PID_START_TICKS_PINNED",source)
        self.assertIn("kill(getpid(),SIGKILL)",source)
        self.assertNotIn("kill(kid",source)
    def test_rescue_is_fenced_when_missing(self):
        r=self.m["rescue"]
        self.assertTrue(r["missing_rescue_sha_rejected"])
        self.assertEqual(r["second_boot_active_files_unchanged_count"],5)
        self.assertEqual(r["baseline_restored_originals"],5)
        for key in ("physical_off_usb_boot_guardian_verified","real_hardware_powerloss_proven",
                    "physical_router_coldboot_tested"):
            self.assertFalse(r[key])
    def test_kernel49_gap_is_explicit(self):
        k=self.m["linux49_compatibility"]
        self.assertEqual(k["historical_kernel"],"4.9-ndm-5")
        self.assertFalse(k["pidfd_open_supported"])
        self.assertFalse(k["pidfd_send_signal_supported"])
        self.assertFalse(k["physical_cap_net_raw_tproxy_proven"])
        self.assertFalse(k["actual_live_s97_s98_s99_watchdog_cron_inventory_complete"])
        self.assertTrue(k["cap_sys_admin_or_cap_dac_override_forbidden_for_untrusted_descendants"])
    def test_physical_production_hard_no_go(self):
        self.assertTrue((ROOT/self.m["prior_release"]).is_file())
        self.assertEqual(self.m["release_decision"],"HARD_NO_GO_PRODUCTION")
        self.assertFalse(any(self.m["authorization"].values()))
        self.assertEqual(self.m["full_system_ci"]["run_id"],41222202057)
        self.assertEqual(self.m["full_system_ci"]["conclusion"],"success")
    def test_staging_only_runner_no_router_actions(self):
        code=(ROOT/"xray/lab/rc9_fullvm_runner.sh").read_text()
        self.assertIn("qemu-system-x86_64",code)
        self.assertIn("RUNNER_TEMP",code)
        self.assertIn("RC9_SCENARIO",code)
        self.assertIn("SECOND_RESCUE=blank-rescue",code)
        self.assertNotIn("ssh root@",code)
        self.assertNotIn("/opt/etc/init.d/",code)
if __name__=="__main__":unittest.main()
