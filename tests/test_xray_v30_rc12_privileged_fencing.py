"""Mutation tests for privileged escape / all legacy entrypoints / no-leak gates."""
from dataclasses import fields, replace
import unittest
from xray.lab.rc12_privileged_fencing_packet_gate import (
    ACTORS, ActorWitness, Proof, evaluate, hypothetical_all_true_fixture)
class RC12Fencing(unittest.TestCase):
    def setUp(self):
        self.good = hypothetical_all_true_fixture()
    def blocked(self, p, reason):
        r = evaluate(p)
        self.assertEqual(r["decision"], "HARD_NO_GO")
        self.assertFalse(r["production_authorized"])
        self.assertFalse(r["hardware_accepted"])
        self.assertFalse(r["router_commands"])
        self.assertTrue(any(reason in s for s in r["reasons"]), r["reasons"])
    def test_synthetic_all_green_cannot_authorize_production(self):
        r = evaluate(self.good)
        self.assertEqual(r["decision"], "OFFLINE_REVIEW_CANDIDATE_ONLY")
        self.assertFalse(r["production_authorized"])
        self.assertFalse(r["hardware_accepted"])
    def test_real_rc11_root_escape_blocks(self):
        self.blocked(replace(self.good, root_cgroup_escape_observed=True),
                     "OBSERVED_PRIVILEGED_CGROUP_V1_ESCAPE")
    def test_all_seven_legacy_surfaces_exactly_once(self):
        self.assertEqual(len(ACTORS), 7)
        self.blocked(replace(self.good, actors=self.good.actors[:-1]), "SEVEN_EXACT")
        self.blocked(replace(self.good, actors=self.good.actors + self.good.actors[:1]),
                     "DUPLICATE")
    def test_every_legacy_actor_requires_each_fencing_ack(self):
        for i, actor in enumerate(self.good.actors):
            for f in fields(ActorWitness):
                if f.name == "name":
                    continue
                with self.subTest(actor=actor.name, evidence=f.name):
                    altered = list(self.good.actors)
                    altered[i] = replace(actor, **{f.name: False})
                    self.blocked(replace(self.good, actors=tuple(altered)),
                                 "LEGACY_ACTOR_UNFENCED")
    def test_each_cas_pid_orphan_packet_no_leak_rescue_gate(self):
        for f in fields(Proof):
            if f.name in ("actors", "root_cgroup_escape_observed"):
                continue
            with self.subTest(gate=f.name):
                self.blocked(replace(self.good, **{f.name: False}), f.name)
    def test_default_evidence_fails_closed(self):
        self.blocked(Proof(), "OBSERVED_PRIVILEGED_CGROUP_V1_ESCAPE")
        self.blocked(Proof(), "guest_mips49_tcp_packets_and_counters")
if __name__ == "__main__":
    unittest.main()
