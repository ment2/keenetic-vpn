"""Offline RC23 destination and UDP return evidence mutation suite."""
from dataclasses import fields, replace
import unittest
from xray.lab.rc23_original_destination_release_gate import Witness,evaluate,synthetic_all_true

class RC23OriginalDestinationGate(unittest.TestCase):
    def setUp(self): self.good=synthetic_all_true()
    def block(self,w,part):
        r=evaluate(w)
        self.assertEqual(r["decision"],"HARD_NO_GO",r)
        self.assertTrue(any(part in x for x in r["reasons"]),r)
        self.assertFalse(r["original_destination_proven"])
        self.assertFalse(r["host_bidirectional_udp_proven"])
        self.assertFalse(r["production_authorized"])
        self.assertFalse(r["router_commands"])
    def test_even_all_true_only_offline_review(self):
        r=evaluate(self.good)
        self.assertEqual(r["decision"],"OFFLINE_REVIEW_CANDIDATE_ONLY")
        self.assertFalse(r["production_authorized"])
        self.assertFalse(r["original_destination_proven"])
    def test_rc21_synthetic_redirect_is_no_go(self):
        r=replace(self.good,no_freedom_redirect_or_destination_rewriting=False,
                  tcp_outbound="127.0.0.1:19292",udp_outbound="127.0.0.1:19292",
                  backend_tcp="127.0.0.1:19292",backend_udp="127.0.0.1:19292")
        self.block(r,"UNPROVEN:no_freedom_redirect")
        self.block(r,"ORIGINAL_DEST_NOT_PRESERVED:udp_outbound")
    def test_each_witness_is_required(self):
        for f in fields(Witness):
            if f.type is bool:
                with self.subTest(f=f.name):
                    self.block(replace(self.good,**{f.name:False}),"UNPROVEN:"+f.name)
    def test_separate_udp_host_return_witness(self):
        self.block(replace(self.good,host_udp_return_payload_exact=False),"host_udp_return_payload_exact")
        self.block(replace(self.good,independent_udp_hostfwd_positive_control=False),"independent_udp_hostfwd_positive_control")
    def test_original_destination_needs_both_protocols_independent_backend(self):
        self.block(replace(self.good,independent_backend_network_stack_verified=False),"independent_backend_network_stack_verified")
        for name in ("tcp_outbound","udp_outbound","backend_tcp","backend_udp"):
            with self.subTest(name=name):
                self.block(replace(self.good,**{name:"10.0.2.15:19292"}),"ORIGINAL_DEST_NOT_PRESERVED:"+name)
    def test_malformed_original_rejected(self):
        for bad in ("","127.0.0.1:0","10.0.2.15:65536","not-an-ip:19191"):
            self.block(replace(self.good,origin=bad),"ORIGINAL_DESTINATION_INVALID")
if __name__=="__main__":unittest.main()
