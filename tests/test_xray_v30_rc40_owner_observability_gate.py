"""RC40 adversarial negative gating using two private UDP owner states."""
from dataclasses import replace
import unittest
from xray.lab.rc40_owner_observability_gate import (
 UdpFiveTuple,ExternalWitness,World,CommitAuthority,
 non_identifiability_witness,release_decision,
)
BOOT="00000000-1111-2222-3333-444444444444"
A=UdpFiveTuple("eth1","10.77.0.1",41271,"10.77.0.3",19301)
B=UdpFiveTuple("eth1","10.77.0.1",59950,"10.77.0.3",19301)
PUBLIC=ExternalWitness(BOOT,3,150,1050,220,1070,frozenset(),frozenset(),"a"*64)
class RC40Observability(unittest.TestCase):
 def test_same_kernel_public_owner_map_not_inferable(self):
  w_old=World(PUBLIC,frozenset({A}))
  w_none=World(PUBLIC,frozenset())
  w=non_identifiability_witness(w_old,w_none)
  self.assertTrue(w["demonstrates_incomplete_inventory"])
  self.assertEqual(w["witness"],"SAME_KERNEL_PACKET_SNAPSHOT_DIFFERENT_XRAY_PRIVATE_OWNER")
  self.assertFalse(w["production_authorized"])
 def test_changed_observable_snapshot_not_a_counterexample(self):
  w_old=World(PUBLIC,frozenset({A}))
  w_new=World(replace(PUBLIC,conntrack_entries=frozenset({A})),frozenset())
  self.assertFalse(non_identifiability_witness(w_old,w_new)["demonstrates_incomplete_inventory"])
 def test_equal_private_maps_not_a_counterexample(self):
  a=World(PUBLIC,frozenset({A}))
  self.assertFalse(non_identifiability_witness(a,a)["demonstrates_incomplete_inventory"])
 def test_private_old_session_hidden_after_kernel_expiry(self):
  r=release_decision(PUBLIC,owner_snapshot=frozenset({A}))
  self.assertIn("PRIVATE_UDP_OWNER_HIDDEN_FROM_KERNEL_CONNTRACK",r["reasons"])
  self.assertEqual(r["decision"],"HARD_NO_GO_PRODUCTION")
 def test_missing_private_map_and_root_fence(self):
  r=release_decision(PUBLIC)
  self.assertIn("NO_COMPLETE_VERIFIED_XRAY_INTERNAL_UDP_OWNER_MAP",r["reasons"])
  self.assertIn("MISSING_INDEPENDENT_RELEASE_WITNESS:mandatory_independent_root_descendant_fence",r["reasons"])
 def test_missing_cookie_kernel_commit_boot_and_rollback(self):
  r=release_decision(PUBLIC)
  for x in ("stable_boot_pid_start_ticks_and_socket_cookies",
            "actual_ingress_freeze_before_capture","kernel_commit_receipt",
            "durable_fsync_generation_cas","original_rules_exact_rollback_ack"):
   self.assertIn("MISSING_INDEPENDENT_RELEASE_WITNESS:"+x,r["reasons"])
 def test_claimed_private_flow_map_must_cover_kernel(self):
  r=release_decision(replace(PUBLIC,conntrack_entries=frozenset({A,B})),
           owner_snapshot=frozenset({A}))
  self.assertIn("KERNEL_UDP_TUPLES_WITHOUT_XRAY_OWNER",r["reasons"])
 def test_all_synthetic_approvals_never_physical_release(self):
  a=CommitAuthority(*([True]*10))
  r=release_decision(PUBLIC,owner_snapshot=frozenset({A}),authority=a)
  self.assertEqual(r["decision"],"HARD_NO_GO_PRODUCTION")
  self.assertFalse(r["production_authorized"])
  self.assertFalse(r["atomic_kernel_commit_proven"])
  self.assertEqual(r["router_actions"],())
if __name__=="__main__":unittest.main()
