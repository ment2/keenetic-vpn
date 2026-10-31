"""Review-only Linux49 parent-owned Xray lab specification integrity."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
SPEC=ROOT/"xray/staging/v30-parent-owned-kernel49-lab-spec-v1.json"


class ParentOwnedReleaseSpecTests(unittest.TestCase):
    def setUp(self):
        self.data=json.loads(SPEC.read_text(encoding="utf-8"))

    def test_exact_git_blob_pins(self):
        for name, expected in self.data["component_git_blob_sha1"].items():
            with self.subTest(path=name):
                raw=(ROOT/name).read_bytes()
                blob=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
                self.assertEqual(blob,expected)

    def test_archived_kernel_is_no_prod(self):
        self.assertEqual(self.data["archived_kernel"],"4.9-ndm-5")
        self.assertEqual(self.data["status"],"LAB_ONLY_NOT_INSTALLABLE")
        self.assertIs(self.data["deploy_authorized"],False)
        self.assertIs(self.data["cutover_authorized"],False)
        self.assertEqual(self.data["router_commands"],[])
        self.assertFalse(self.data["lab_evidence"]["kernel49_hardware_tested"])
        self.assertFalse(self.data["lab_evidence"]["native_mips_kernel_tproxy_tested"])

    def test_no_pidfd_for_linux49(self):
        self.assertEqual(set(self.data["excluded_kernel_primitives"]),
                         {"pidfd_open","pidfd_send_signal"})
        self.assertIn("waitid(P_PID,WEXITED|WNOHANG|WNOWAIT)",
                      self.data["required_kernel_primitives"])
        self.assertIn("prctl(PR_SET_PDEATHSIG)",
                      self.data["required_kernel_primitives"])

    def test_guardian_never_kills_orphan(self):
        self.assertIn("guardian_never_signals_stale_journal_pid",
                      self.data["safety_invariants"])
        self.assertIn("guardian_aborts_if_candidate_pid_ticks_still_alive",
                      self.data["safety_invariants"])

    def test_release_pair_with_existing_unchanged_rescue_manifest(self):
        self.assertTrue((ROOT/self.data["paired_supervisor_manifest"]).is_file())
        self.assertTrue((ROOT/self.data["paired_rescue_contract"]).is_file())
        self.assertIn("root_only_boot_rescue_independent_of_Entware_USB",
                      self.data["mandatory_remaining_live_proofs"])

    def test_ci_four_real_mips_scenarios_pinned(self):
        self.assertEqual(self.data["lab_evidence"]["mips_ci"],"41211906271")
        self.assertEqual(set(self.data["lab_evidence"]["confirmed_scenarios"]),
                         {"parent_crash","child_exit","rollback","prepared"})
        self.assertIn("SOCKS5_UDP_ASSOCIATE",self.data["lab_evidence"]["transport"])


if __name__=="__main__":
    unittest.main()
