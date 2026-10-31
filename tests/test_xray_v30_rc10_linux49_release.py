"""RC10 pinned-source, true Linux4.9 QEMU and split native TPROXY safety gate."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
RELEASE=ROOT/"xray/staging/v30-rc10-linux49-capability-tproxy-cas-rescue-review.json"
class RC10Gates(unittest.TestCase):
    def setUp(self):
        self.m=json.loads(RELEASE.read_text(encoding="utf8"))
    def test_seven_exact_git_blob_hashes(self):
        self.assertEqual(len(self.m["source_blobs"]),7)
        for name,expected in self.m["source_blobs"].items():
            with self.subTest(file=name):
                # Historical RC10 manifest attests archived bytes, not the later PIDFD revision.
                historical_aliases = {
                    "xray/lab/rc10_native_tproxy_minimal_caps.sh": "xray/lab/archive/rc10_native_tproxy_minimal_caps_historical.sh",
                    ".github/workflows/xray-v30-rc10-native-cap-tproxy.yml": ".github/archive/xray-v30-rc10-native-cap-tproxy-historical.yml",
                }
                pinned_path = historical_aliases.get(name, name)
                raw=(ROOT/pinned_path).read_bytes()
                digest=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
                self.assertEqual(digest,expected)
    def test_kernel49_binary_sha_and_xray_sha_pinned(self):
        p=self.m["pin"]
        self.assertEqual(p["debian_package_sha256"],"d410dd577fac677bb50978d5fe91b622d1520b783cb4ef23a1bcd7851606e326")
        self.assertEqual(p["extracted_vmlinuz_sha256"],"cc91d3c764694426a4e830da226da61f60a97d074986aa47bb9102ad8792e4c0")
        self.assertEqual(p["xray_zip_sha256"],"29ce535b56e207a406ffa1c2d4842dcc410be003eff8ec508bb732abc9f8e385")
        self.assertEqual(p["xray_native_executable_sha256"],"3f650abf1fc4a4fbf5abe7fc9990a2658020907cd984214e9c075b4b00989fea")
    def test_true_fullsystem_kernel49_but_not_vendor_mips(self):
        g=self.m["fullsystem"]
        self.assertEqual(g["ci"],41224765496)
        self.assertEqual(g["conclusion"],"success")
        self.assertEqual(g["kernel"],"4.9.0-13-amd64")
        self.assertEqual(g["arch"],"x86_64")
        self.assertIn("full-system",g["qemu_mode"])
        self.assertTrue(g["PR_GET_NO_NEW_PRIVS_after_exec_one"])
        self.assertTrue(g["cap_raw_tcp_udp_ip_transparent_allowed"])
        self.assertTrue(g["real_xray_tproxy_inbound_started"])
        self.assertFalse(g["real_mips_keenetic_vendor_ndm5_proven"])
        self.assertFalse(g["kernel49_full_tproxy_packet_flow_proven"])
        self.assertTrue(g["privileged_cgroup_migration_succeeded"])
    def test_guardian_actual_cas_and_parent_death_not_full_physical(self):
        g=self.m["fullsystem"]
        self.assertEqual(g["guardian_cas_generations"],3)
        self.assertEqual(g["guardian_cas_independent_processes_per_generation"],8)
        self.assertTrue(g["crashed_prepared_not_committed_or_replayed"])
        self.assertTrue(g["real_xray_parent_sigkill_pdeathsig_direct_child_stopped"])
        self.assertFalse(g["full_legacy_s97_s98_s99_watchdog_cron_fencing_proven"])
    def test_kernel49_three_two_boot_rescue_scenarios(self):
        r=self.m["fullsystem"]
        self.assertEqual(r["scenario_boot_pairs"],3)
        self.assertEqual(r["scenarios"],["baseline","rescue-missing","rescue-absent"])
        self.assertEqual(r["blank_rescue_file_write_count"],0)
        self.assertEqual(r["physically_detached_rescue_file_write_count"],0)
        self.assertEqual(r["baseline_restored_originals"],5)
        self.assertFalse(r["physical_powerloss_proven"])
        self.assertFalse(r["physical_device_separation_proven"])
    def test_native_packet_path_separate_from_kernel49(self):
        n=self.m["native_packet"]
        self.assertEqual(n["ci"],41224152158)
        self.assertEqual(n["conclusion"],"success")
        self.assertTrue(n["iptables_tproxy_TCP_packets"])
        self.assertTrue(n["iptables_tproxy_UDP_packets"])
        self.assertTrue(n["FORWARD_DROP_on_dead_xray"])
        self.assertFalse(n["actual_kernel49_same_packet_path_proven"])
    def test_release_and_router_operations_unconditionally_denied(self):
        self.assertFalse(any(self.m["authorization"].values()))
        self.assertFalse(any(self.m["physical_release_gates"].values()))
        self.assertEqual(self.m["release_decision"],"HARD_NO_GO_PRODUCTION")
        self.assertTrue((ROOT/self.m["prior_rc9"]).is_file())
    def test_kernel49_cas_source_has_fsync_and_no_pid_killall(self):
        src=(ROOT/"xray/lab/rc10_guest_guardian_generation_cas.c").read_text()
        self.assertIn("flock(fd,LOCK_EX)",src)
        self.assertIn("fsync(fd)",src)
        self.assertIn("fsync",src)
        self.assertIn("rename(path,LEDGER)",src)
        self.assertIn("kill(getpid(),SIGKILL)",src)
        self.assertNotIn("killall",src)
        self.assertNotIn("/opt/",src)
    def test_hardware_no_go_has_explicit_legacy_escape(self):
        self.assertGreaterEqual(len(self.m["limitations"]),6)
        self.assertIn("Root/privileged descendant escapes cgroup v1: legacy actors remain unfenced",self.m["limitations"])
if __name__=="__main__":
    unittest.main()
