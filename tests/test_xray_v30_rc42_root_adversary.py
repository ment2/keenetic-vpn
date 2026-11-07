"""Only disposable GitHub runner root actor is allowed in RC42; no router."""
from pathlib import Path
import unittest
R=Path(__file__).resolve().parents[1]
N=(R/"xray/lab/rc42_root_adversary_netns.sh").read_text()
E=(R/"xray/lab/rc42_root_adversary_endpoint.py").read_text()
S=(R/"xray/lab/rc42_root_adversary_runner.sh").read_text()
class ScopedRoot(unittest.TestCase):
 def test_root_adversary_attacks_only_disposable_netns(self):
  self.assertIn("sudo unshare --net",S)
  self.assertIn('nft delete table inet rc42',N)
  self.assertIn('flock -x 9',N)
  self.assertIn('flock -n "$W/controller.lock" true',N)
 def test_independent_root_process_and_actual_packet_after_attack(self):
  self.assertIn("RC42_TEST_ONLY_ROOT_CHILD",N)
  self.assertIn("RC42_ROOT_ADVERSARY_SAME_KERNEL_UNDER_CONTROLLER_FLOCK",N)
  self.assertIn("RC42_ROOT_PACKET_BYPASS_WHILE_LEDGER_SAYS_FROZEN",N)
  self.assertIn("RC42_CLIENT_BYPASS_EXACT_ECHO",N)
  self.assertIn('"BYPASS"',E)
 def test_stale_frozen_generation_receipt_is_not_kernel_authority(self):
  self.assertIn("RC42_RUNNER_FSYNC_DIR_CAS 2 FROZEN_DROP",N)
  self.assertIn('cmp "$W/original.nft" "$W/root-overwrite.nft"',N)
  self.assertIn("ROOT_CHILD",S)
 def test_original_ruleset_after_bypass_restored_only_not_atomic_owner_commit(self):
  self.assertIn('cmp "$W/original.nft" "$W/restored.nft"',N)
  self.assertIn("RC42_HARD_NO_GO_DROP_IS_NOT_BUFFERED_ATOMIC_SESSION_FREEZE",N)
 def test_no_physical_root_or_router_process(self):
  for bad in ["killall xray","ssh root@","StrictHostKeyChecking=no","PRODUCTION_AUTHORIZED"]:
   self.assertNotIn(bad,N+S+E)
if __name__=="__main__":unittest.main()
