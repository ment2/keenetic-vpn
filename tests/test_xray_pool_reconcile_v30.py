"""Offline v30 continuity policy tests, no router or VPN access."""
import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "xray/lab/pool_reconcile_v30.py"
spec = importlib.util.spec_from_file_location("pool_reconcile_v30", SOURCE)
import sys
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
reconcile = module.reconcile


class PoolReconcileTests(unittest.TestCase):
    def test_reorder_preserves_active(self):
        p = reconcile(("a", "b"), ("b", "a"), "a")
        self.assertEqual((p.action, p.selected, p.standby), ("keep", "a", ("b",)))

    def test_add_new_standby_does_not_switch(self):
        p = reconcile(("a",), ("a", "b"), "a")
        self.assertEqual((p.action, p.selected, p.standby), ("keep", "a", ("b",)))

    def test_remove_other_server_does_not_switch(self):
        p = reconcile(("a", "b"), ("a", "c"), "a")
        self.assertEqual(p.action, "keep")
        self.assertEqual(p.retired, ("b",))

    def test_active_removed_switches_new_flows(self):
        p = reconcile(("a", "b"), ("b", "c"), "a")
        self.assertEqual((p.action, p.selected), ("switch_new_flows", "b"))

    def test_failed_active_switches_new_flows(self):
        p = reconcile(("a", "b"), ("a", "b"), "a", frozenset({"a"}))
        self.assertEqual((p.action, p.selected), ("switch_new_flows", "b"))

    def test_empty_new_pool_holds_last_known_good(self):
        p = reconcile(("a",), (), "a")
        self.assertEqual((p.action, p.selected), ("hold_fail_closed", "a"))

    def test_empty_new_pool_failed_active_has_no_selected(self):
        p = reconcile(("a",), (), "a", frozenset({"a"}))
        self.assertEqual((p.action, p.selected), ("hold_fail_closed", None))

    def test_duplicate_fingerprints_rejected(self):
        with self.assertRaises(ValueError):
            reconcile(("a",), ("a", "a"), "a")

    def test_active_not_in_old_rejected(self):
        with self.assertRaises(ValueError):
            reconcile(("a",), ("b",), "missing")

    def test_first_activation(self):
        p = reconcile((), ("a", "b"), None)
        self.assertEqual((p.action, p.selected), ("switch_new_flows", "a"))


if __name__ == "__main__":
    unittest.main()
