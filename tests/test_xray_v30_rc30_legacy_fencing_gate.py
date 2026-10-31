"""All dangerous legacy restart actors force HARD NO-GO for first cutover."""
import unittest
from xray.lab.rc30_legacy_fencing_readonly_audit import audit,SNAPSHOTS
class RC30LegacyFencing(unittest.TestCase):
 def test_snapshot_sources_present(self):
  r=audit()
  self.assertFalse(any(x.startswith("MISSING_LEGACY_SOURCE") for x in r["reasons"]))
  self.assertEqual(len(SNAPSHOTS),5)
 def test_observed_restart_collision_and_killall(self):
  r=audit()
  for reason in ("S97_KILLALL_CAN_KILL_BOTH_INGRESS_OWNERS",
   "ROOT_WATCHDOG_CAN_RESTART_S97_DURING_CUTOVER",
   "S98_CAN_REWRITE_TPROXY_DURING_CUTOVER",
   "S99_PID_ONLY_STOP_NO_START_TICKS_OR_DESCENDANT_FENCE",
   "CRON_SUBSCRIPTION_UPDATER_CAN_RESTART_LEGACY"):
   with self.subTest(reason=reason): self.assertIn(reason,r["reasons"])
 def test_no_shared_cas_lock_for_all_versioned_actors(self):
  r=audit()
  for actor in SNAPSHOTS:
   self.assertIn("NO_SHARED_GENERATION_LOCK:"+actor,r["reasons"])
 def test_never_accept_offline_fences_as_production(self):
  r=audit()
  self.assertEqual(r["decision"],"HARD_NO_GO")
  self.assertFalse(r["fencing_proven"])
  self.assertFalse(r["production_authorized"])
  self.assertEqual(r["router_actions"],())
  self.assertIn("NO_VERIFIED_GENERIC_UDP_FLOW_PINNING",r["reasons"])
 def test_missing_snapshot_also_denied(self):
  from tempfile import TemporaryDirectory
  from pathlib import Path
  with TemporaryDirectory() as root:
   r=audit(Path(root))
   self.assertEqual(r["decision"],"HARD_NO_GO")
   self.assertTrue(any(x.startswith("MISSING_LEGACY_SOURCE:") for x in r["reasons"]))
if __name__=="__main__":unittest.main()
