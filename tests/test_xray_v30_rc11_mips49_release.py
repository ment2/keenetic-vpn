"""RC11: exact source and real MIPS32LE vs packet/physical evidence separation."""
import hashlib
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
DOC=ROOT/"xray/staging/v30-rc11-mips49-fullsystem-legacy-fencing-review.json"
class RC11ReleaseGates(unittest.TestCase):
    def setUp(self):
        self.d=json.loads(DOC.read_text(encoding="utf8"))
    def test_all_eight_git_blob_sha_pins(self):
        self.assertEqual(len(self.d["source_blobs"]),8)
        for name,want in self.d["source_blobs"].items():
            with self.subTest(path=name):
                raw=(ROOT/name).read_bytes()
                actual=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
                self.assertEqual(actual,want)
    def test_kernel_and_official_mips_xray_exact_hashes(self):
        p=self.d["archive_pins"]
        self.assertEqual(p["kernel_deb_sha256"],"9a5dff9c498bf5736ca9f97cbb005b4b60bd139aa0f30f5bab9feca783907d9b")
        self.assertEqual(p["kernel_vmlinux_sha256"],"20f5380e02f2e40d4495fd61a854e5867f5ccdf95c8c1fd3d53fe27e8be1797f")
        self.assertEqual(p["xray_archive_sha256"],"1590b2bcefe64fb0604f29c8c75219bfbe8f63daa3bc8e3956edfa6da97c5869")
        self.assertEqual(p["xray_executable_sha256"],"3d2588c5ef770a6a7e1bfdd5db511130fb3acd79eb91bfcb108753b3e1dda1f6")
        self.assertFalse(p["source_signature_verified"])
    def test_real_mips_fullsystem_success_but_no_packet_claim(self):
        e=self.d["evidence"]["mips_fullsystem_ci"]
        self.assertEqual(e["id"],41226245794)
        self.assertEqual(e["conclusion"],"success")
        self.assertEqual(e["guest_kernel"],"4.9.0-13-4kc-malta")
        self.assertTrue(e["real_kernel_mipsel"])
        self.assertTrue(e["genuine_xray_mips32le"])
        self.assertEqual(e["only_cap_net_raw_effective_mask"],"0x2000")
        self.assertEqual(e["PR_GET_NO_NEW_PRIVS_after_exec"],1)
        for name in ("guest_tproxy_ipv4_tcp_packet_forwarding_verified",
                     "guest_tproxy_ipv4_udp_packet_forwarding_verified",
                     "guest_tproxy_ipv6_packet_forwarding_verified",
                     "guest_dns_no_leak_verified","guest_stable_kill_switch_verified"):
            self.assertFalse(e[name],name)
    def test_root_cgroup_escape_must_remain_hard_no_go(self):
        e=self.d["evidence"]["mips_fullsystem_ci"]
        self.assertTrue(e["real_mips_privileged_cgroup_escape_succeeded"])
        self.assertTrue(e["real_mips_eight_nonroot_descendants_cannot_escape"])
        self.assertTrue(e["real_mips_unknown_orphan_prevents_restart"])
        self.assertFalse(self.d["physical_acceptance"]["privileged_cgroup_escape_prevented"])
    def test_guest_three_real_cas_generations_and_direct_child(self):
        e=self.d["evidence"]["mips_fullsystem_ci"]
        self.assertTrue(e["real_mips_guardian_cas_three_generations_eight_processes"])
        self.assertTrue(e["real_mips_crashed_prepared_did_not_commit"])
        self.assertTrue(e["real_mips_xray_direct_parent_owned_pid_start_ticks"])
    def test_reuse_existing_virtual_rescue_only(self):
        old=self.d["evidence"]["previous_rc10"]
        self.assertEqual(old["virtual_rescue_baseline_restored"],5)
        self.assertEqual(old["virtual_rescue_missing_writes"],0)
        self.assertEqual(old["virtual_rescue_detached_writes"],0)
        self.assertTrue((ROOT/old["previous_review"]).is_file())
    def test_legacy_review_only_no_authorization(self):
        c=self.d["evidence"]["legacy_fencing_contract"]
        self.assertEqual(c["exact_actor_count"],7)
        self.assertEqual(c["archived_source_hash_count"],5)
        self.assertTrue(c["rejects_root_escape"])
        self.assertTrue(c["rejects_pid_reuse_and_socket_inodes"])
        self.assertTrue(c["review_only_even_with_synthetic_all_true"])
        self.assertEqual(self.d["decision"],"HARD_NO_GO_PRODUCTION")
        self.assertFalse(any(self.d["physical_acceptance"].values()))
        self.assertFalse(any(self.d["authorization"].values()))
    def test_guest_source_cannot_signal_router(self):
        text=(ROOT/"xray/lab/rc11_mips49_guest_init.c").read_text()
        self.assertIn("kill(x,SIGTERM)",text)
        self.assertIn("waitpid(x,&st,0)",text)
        self.assertNotIn("killall(",text)  # reject executable call, not a comment describing its absence
        self.assertNotIn("ssh ",text)
        self.assertNotIn("/opt/",text)
    def test_runner_enforces_no_mips_full_tproxy_claim(self):
        r=(ROOT/"xray/lab/rc11_mips49_fullsystem_runner.sh").read_text()
        self.assertIn("REAL_MIPS49_FULL_TPROXY_PACKETS_NOT_TESTED",r)
        self.assertIn("HARD_NO_GO_PHYSICAL_VENDOR_NDM5_MIPS_UNKNOWN",r)
        self.assertIn("PRIVILEGED_CGROUP_ESCAPE_SUCCEEDED_HARD_NO_GO",r)
        self.assertIn("1590b2bcefe64fb0604f29c8c75219bfbe8f63daa3bc8e3956edfa6da97c5869",r)

if __name__=="__main__":
    unittest.main()
