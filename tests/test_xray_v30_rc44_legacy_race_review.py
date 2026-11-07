"""Versioned supervisor and cron source timing counterexamples (offline only)."""
import unittest
from xray.lab.rc44_legacy_race_review import source_review,duplicate_forward_counterexample,wifi_repair_race_fixture
class Cases(unittest.TestCase):
 def test_source_guard_fields(self):
  r=source_review()
  self.assertTrue(r["wifi_flushes_before_tproxy"])
  self.assertFalse(r["wifi_mangle_write_has_shared_lock"])
 def test_s98_retry_interval(self):
  self.assertEqual(source_review()["s98_repair_loop_period_seconds"],60)
 def test_kill_switch_watch_interval(self):
  self.assertEqual(source_review()["ks_watch_period_seconds"],15)
 def test_forward_dup_from_preexisting_lower_rule(self):
  original=("-A FORWARD -j OTHER","-A FORWARD -j XRAY_KS_HOME")
  updated=duplicate_forward_counterexample(original)
  self.assertEqual(updated.count("-A FORWARD -j XRAY_KS_HOME"),2)
 def test_forward_stable_if_first_rule(self):
  start=("-A FORWARD -j XRAY_KS_HOME","-A FORWARD -j OTHER")
  self.assertEqual(duplicate_forward_counterexample(start),start)
 def test_competing_s98_clobbers_repaired_tproxy_if_unfenced(self):
  x=wifi_repair_race_fixture()
  self.assertEqual(x["before_tproxy"],9)
  self.assertEqual(x["after_operator_repair"],11)
  self.assertEqual(x["after_uncoordinated_s98_failed_rebuild"],9)
  self.assertFalse(x["preserves_operator_repair"])
 def test_cron_can_create_ephemeral_xray_during_canary_preflight(self):
  r=source_review()
  self.assertTrue(r["hourly_spawns_short_lived_xray_binary_for_config_test"])
  self.assertFalse(r["hourly_staged_only_not_live_apply"] is False)
 def test_source_is_not_physical_proof_or_permission(self):
  r=source_review()
  self.assertFalse(r["production_authorized"])
  self.assertFalse(r["root_descendants_quiesced_proven"])
if __name__=="__main__":unittest.main()
