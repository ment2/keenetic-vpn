"""RC33 negative physical/UDP release contracts; no hardware access."""
import unittest
from dataclasses import replace
from xray.lab.rc33_dynamic_udp_release_gate import Flow,Evidence,evaluate
A=Flow("10.77.0.1",42001,"10.77.0.3",19301,"udp","eth1")
B=Flow("10.77.0.1",42002,"10.77.0.3",19301,"udp","eth1")
C=Flow("10.77.0.1",42003,"10.77.0.3",19301,"udp","eth1")
def known():
 return Evidence(boot_id="00000000-1111-2222-3333-444444444444",
   observed_boot_id="00000000-1111-2222-3333-444444444444",
   generation=4,observed_generation=4,
   old_client_sockets=(A,B),captured_incoming=(B,A),
   old_kernel_owner_rules=(A,B),new_kernel_owner_packets=1,
   rollback_old_socket_bytes_proven=True,
   old_xray_pid_startticks_preserved=True,
   new_xray_pid_startticks_preserved=True)
class DynamicGate(unittest.TestCase):
 def test_even_perfect_synthetic_scope_is_not_physical(self):
  e=known();r=evaluate(e)
  self.assertEqual(r["decision"],"HARD_NO_GO")
  self.assertFalse(r["production_authorized"])
  self.assertIn("PHYSICAL_HARD_NO_GO:physically_fenced_seven_privileged_legacy",r["reasons"])
 def test_silent_third_old_udp_socket_blocks_cutover(self):
  r=evaluate(replace(known(),old_client_sockets=(A,B,C)))
  self.assertIn("SILENT_OR_UNOBSERVED_OLD_UDP_ASSOCIATION",r["reasons"])
 def test_new_udp_owner_not_counted_is_blocked(self):
  r=evaluate(replace(known(),new_kernel_owner_packets=0))
  self.assertIn("NEW_UDP_CANDIDATE_OWNER_UNPROVEN",r["reasons"])
 def test_each_identity_dimension_matters(self):
  for part in ("source","sport","destination","dport","protocol","interface"):
   with self.subTest(part=part):
    value={"source":"10.77.0.4","sport":42014,"destination":"10.77.0.2",
      "dport":19302,"protocol":"tcp","interface":"eth0"}[part]
    actual=replace(A,**{part:value})
    r=evaluate(replace(known(),captured_incoming=(actual,B)))
    self.assertEqual(r["decision"],"HARD_NO_GO")
    self.assertIn("SILENT_OR_UNOBSERVED_OLD_UDP_ASSOCIATION",r["reasons"])
 def test_stale_boot_and_generation_mutations_fail(self):
  for change in ({"observed_boot_id":"other"},
                 {"observed_generation":3},
                 {"old_kernel_owner_rules":(A,)},
                 {"rollback_old_socket_bytes_proven":False},
                 {"old_xray_pid_startticks_preserved":False}):
   self.assertEqual(evaluate(replace(known(),**change))["decision"],"HARD_NO_GO")
 def test_no_false_release_even_all_synthetic_physical(self):
  e=replace(known(),physically_fenced_seven_privileged_legacy=True,
    vendor_kernel_live_verified=True,usb_independent_physical_rescue=True)
  r=evaluate(e)
  self.assertEqual(r["decision"],"OFFLINE_KNOWN_FLOW_REVIEW_ONLY")
  self.assertFalse(r["production_authorized"])
  self.assertFalse(r["all_live_udp_flows_certified"])
  self.assertFalse(r["physical_legacy_fencing_proven"])
  self.assertEqual(r["router_commands"],())
if __name__=="__main__":unittest.main()
