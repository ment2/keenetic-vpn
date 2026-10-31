"""Mutation-test each independently necessary physical and lab packet gate."""
import unittest
from dataclasses import fields,replace
from xray.lab.rc20_packet_release_gate import Witness,evaluate
class PacketReleaseGate(unittest.TestCase):
 def test_empty_evidence_fails_closed(self):
  p=evaluate(Witness())
  self.assertEqual(p["state"],"HARD_NO_GO")
  self.assertFalse(p["production_authorized"])
  self.assertEqual(p["router_commands"],[])
 def test_every_independent_witness_can_block(self):
  all_true=Witness(**{f.name:True for f in fields(Witness)})
  for f in fields(Witness):
   with self.subTest(field=f.name):
    p=evaluate(replace(all_true,**{f.name:False}))
    self.assertEqual(p["state"],"HARD_NO_GO")
    self.assertIn(f.name,p["reasons"])
    self.assertFalse(p["production_authorized"])
 def test_synthetic_all_green_does_not_authorize_production(self):
  all_true=Witness(**{f.name:True for f in fields(Witness)})
  p=evaluate(all_true)
  self.assertEqual(p["state"],"OFFLINE_REVIEW_CANDIDATE_ONLY")
  self.assertFalse(p["production_authorized"])
  self.assertFalse(p["hardware_certified"])
 def test_rc19_guest_udp_receipt_is_not_udp_return_or_xray(self):
  p=evaluate(Witness(guest_pcnet_ethernet_packet_ingress=True))
  for missing in ["udp_client_received_same_payload","real_xray_mips_inbound_udp_observed","process_death_no_tcp_udp_direct_fallback","privileged_root_cgroup_v1_escape_independently_fenced"]:
   self.assertIn(missing,p["reasons"])
if __name__=="__main__":unittest.main()
