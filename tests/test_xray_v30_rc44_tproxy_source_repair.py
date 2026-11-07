"""RC44 strictly offline source and repair-plan contract."""
import unittest
from xray.lab.rc44_tproxy_repair_gate import (pinned_source_review,current_chain_lines,
 sha_lines,EXCEPTIONS,LIVE_RC43_CHAIN_SHA256,LiveWitness,review,minimal_iptables_restore_batch)
from xray.lab.rc44_wifi_rules_failure_injection import reproduce
class RC44(unittest.TestCase):
 def test_rc43_live_chain_sha_exactly_expected_nine_return_source(self):
  self.assertEqual(sha_lines(current_chain_lines()),LIVE_RC43_CHAIN_SHA256)
  self.assertEqual(len(EXCEPTIONS),9)
 def test_exact_pinned_shell_has_unhandled_tproxy_add(self):
  self.assertTrue(pinned_source_review()["unhandled_tproxy_append_failure_possible"])
 def test_real_shell_executed_against_mock_kernel_returns_zero_on_rejection(self):
  x=reproduce()
  self.assertEqual(x["shell_exit_code"],0)
  self.assertEqual(x["return_destinations"],9)
  self.assertEqual(x["tproxy_add_failures"],2)
 def test_minimal_transaction_only_appends_two(self):
  s=minimal_iptables_restore_batch()
  self.assertEqual(s.count("-A XRAY_WIFI"),2)
  self.assertEqual(s.count("-F XRAY_WIFI"),0)
  self.assertIn("*mangle",s)
  self.assertIn("COMMIT",s)
 def test_no_go_even_with_all_model_checks_true(self):
  d=LiveWitness(boot_id="1"*36,xray_pid=815,start_ticks=4570,
   wifi_chain_sha256=LIVE_RC43_CHAIN_SHA256,same_listener_owner=True,
   target_tproxy_supported=True,original_mangle_snapshot_verified=True,
   rollback_rehearsed_on_target=True,root_descendants_quiesced=True,
   ipv4_ipv6_failclosed_verified=True,local_recovery_verified=True)
  self.assertFalse(review(d)["production_authorized"])
  self.assertEqual(review(d)["decision"],"HOLD_REAL_ROUTER_REPAIR")
 def test_stale_chain_and_process_gates(self):
  x=review(LiveWitness())
  self.assertIn("CHAIN_STATE_DRIFT_OR_NINE_RETURN_BASE_NOT_CONFIRMED",x["reasons"])
  self.assertIn("CURRENT_BOOT_PID_START_TICKS_UNVERIFIED",x["reasons"])
 def test_rollback_selectors_delete_only_owned_rules(self):
  x=review()
  self.assertEqual(len(x["rollback_rule_selectors"]),2)
  self.assertTrue(all(s.startswith("-D XRAY_WIFI ") for s in x["rollback_rule_selectors"]))
if __name__=="__main__":unittest.main()
