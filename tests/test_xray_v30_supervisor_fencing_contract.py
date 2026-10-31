"""Synthetic-only descendant-fencing safety contracts; no live router commands."""
from dataclasses import fields, replace
import json
import unittest

from xray.lab import v30_supervisor_fencing_contract as gate


class SupervisorFencingContractTests(unittest.TestCase):
    def test_frozen_production_legacy_supervision_cannot_cutover(self):
        reasons = gate.frozen_router_risks()
        for expected in (
            "S97_GLOBAL_KILLALL", "WATCHDOG_NO_COOPERATIVE_MUTEX",
            "S98_RULES_MUTATE_WITHOUT_SHARED_MUTEX", "WIFI_TPROXY_CHAIN_FLUSH",
        ):
            self.assertIn(expected, reasons)
        self.assertTrue(gate.release_gate(gate.Proof(), source_hazards=reasons))

    def test_every_missing_proof_blocks_even_when_other_proofs_pass(self):
        full = gate.Proof(**{f.name: True for f in fields(gate.Proof)})
        self.assertEqual(gate.release_gate(full), ())
        for item in fields(gate.Proof):
            with self.subTest(item=item.name):
                partial = replace(full, **{item.name: False})
                self.assertIn("UNPROVEN_" + item.name.upper(), gate.release_gate(partial))

    def test_stopped_parent_has_live_child_that_can_run_killall(self):
        p = (gate.Process(32713, 1, 11, "T", "watchdog"),
             gate.Process(32714, 32713, 12, "S", "S97 restart"),
             gate.Process(32715, 32714, 13, "R", "killall xray"),
             gate.Process(24097, 1, 14, "T", "wifi"))
        self.assertEqual([x.pid for x in gate.descendants(p, 32713)], [32714, 32715])
        self.assertIn("UNFENCED_DESCENDANTS",
                      gate.release_gate(gate.Proof(), processes=p,
                                        watchdog_pid=32713, wifi_pid=24097))

    def test_stopped_parent_has_active_wifi_rules_descendant(self):
        p = (gate.Process(32713, 1, 11, "T", "watchdog"),
             gate.Process(24097, 1, 12, "T", "wifi"),
             gate.Process(25000, 24097, 13, "S", "wifi rules"),
             gate.Process(25001, 25000, 14, "R", "iptables -F XRAY_WIFI"))
        self.assertIn("UNFENCED_DESCENDANTS",
                      gate.release_gate(gate.Proof(), processes=p,
                                        watchdog_pid=32713, wifi_pid=24097))

    def test_running_parent_not_fenced(self):
        p = (gate.Process(32713, 1, 11, "S", "watchdog"),
             gate.Process(24097, 1, 12, "T", "wifi"))
        self.assertIn("WATCHER_NOT_ACTUALLY_STOPPED",
                      gate.release_gate(gate.Proof(), processes=p,
                                        watchdog_pid=32713, wifi_pid=24097))

    def test_missing_pid_and_duplicate_pid_fail_closed(self):
        self.assertRaises(ValueError, gate.descendants, (), 42)
        bad=(gate.Process(20,1,1,"T","watchdog"),
             gate.Process(20,1,2,"R","evil"))
        self.assertRaises(ValueError, gate.descendants, bad, 20)

    def test_zero_ticks_and_pid_one_are_invalid(self):
        self.assertRaises(ValueError, gate.descendants,
                          (gate.Process(20,1,0,"S","watchdog"),), 20)
        self.assertRaises(ValueError, gate.descendants,
                          (gate.Process(1,0,1,"S","init"),), 1)

    def test_watcher_pid_alias_does_not_prove_safe(self):
        p=(gate.Process(20,1,5,"T","watchdog"),)
        self.assertIn("WATCHER_IDENTITY_UNCERTAIN",
                      gate.release_gate(gate.Proof(), processes=p,
                                        watchdog_pid=20,wifi_pid=20))

    def test_parent_pid_snapshot_absence_not_enough_to_cutover(self):
        p=(gate.Process(20,1,5,"T","watchdog"),
           gate.Process(30,1,8,"T","wifi"))
        missing=gate.release_gate(gate.Proof(), processes=p,watchdog_pid=20,wifi_pid=30)
        self.assertNotIn("UNFENCED_DESCENDANTS",missing)
        self.assertIn("UNPROVEN_COOPERATIVE_SUPERVISOR_LOCK",missing)
        self.assertIn("UNPROVEN_COOPERATIVE_WIFI_LOCK",missing)

    def test_global_killall_is_disallowed_even_with_all_other_proofs(self):
        good=gate.Proof(**{f.name: True for f in fields(gate.Proof)})
        self.assertIn("S97_GLOBAL_KILLALL",
                      gate.release_gate(good,source_hazards=("S97_GLOBAL_KILLALL",)))

    def test_unknown_supervisor_source_is_not_assumed_safe(self):
        hazards=gate.unsafe_legacy_sources(watchdog="restart S97",
                s97="killall xray",s98="iptables -t mangle -F",
                wifi_rules="iptables -F XRAY_WIFI")
        self.assertIn("S97_GLOBAL_KILLALL",hazards)
        self.assertIn("WATCHDOG_NO_COOPERATIVE_MUTEX",hazards)
        self.assertIn("WIFI_TPROXY_CHAIN_FLUSH",hazards)

    def test_no_proof_all_true_on_real_frozen_snapshot(self):
        good=gate.Proof(**{f.name: True for f in fields(gate.Proof)})
        self.assertTrue(gate.release_gate(good,source_hazards=gate.frozen_router_risks()))

    def test_source_emits_no_production_actions(self):
        from inspect import getsource
        source=getsource(gate)
        for unsafe in ("os.kill(", "subprocess.", "iptables -t mangle -F", "S97xray restart"):
            self.assertNotIn(unsafe,source)

    def test_default_is_strictly_fail_closed(self):
        p=gate.Proof()
        self.assertEqual(len(gate.release_gate(p)),len(gate.REQUIRED))


if __name__ == "__main__":
    unittest.main()
