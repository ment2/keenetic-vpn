"""Pool refresh seamlessness: no spurious switch, no stale CAS, no bad endpoint."""
from dataclasses import replace
from threading import Barrier, Thread
import unittest
from xray.lab.pool_generation_v30 import (
    Coordinator, Generation, Proposal, StaleGeneration, UnsafeActivation
)

def approve(co, p):
    return co.commit(p, validated=True, api_healthy=True,
                     continuity_verified=True)


class PoolRefreshCAS(unittest.TestCase):
    def setUp(self):
        self.co = Coordinator(Generation(41, ("a", "b"), "a"))

    def test_reordering_never_changes_active(self):
        state = approve(self.co, self.co.prepare(("b", "a")))
        self.assertEqual(state.active, "a")
        self.assertEqual(state.pool, ("b", "a"))

    def test_qualified_standby_addition_never_switches(self):
        p = self.co.prepare(("c", "b", "a"))
        self.assertEqual(p.plan.action, "keep")
        s = approve(self.co, p)
        self.assertEqual((s.active, s.pool), ("a", ("c", "b", "a")))

    def test_failed_candidate_is_not_persisted(self):
        p = self.co.prepare(("a", "b", "c"), frozenset({"c"}))
        s = approve(self.co, p)
        self.assertEqual((s.active, s.pool), ("a", ("a", "b")))
        self.assertNotIn("c", s.pool)

    def test_failed_active_replaced_for_new_flows(self):
        p = self.co.prepare(("a", "b", "c"), frozenset({"a", "c"}))
        self.assertEqual(p.plan.action, "switch_new_flows")
        s = approve(self.co, p)
        self.assertEqual((s.active, s.pool), ("b", ("b",)))

    def test_empty_or_all_failed_pool_does_not_mutate(self):
        for p in (self.co.prepare(()),
                  self.co.prepare(("a", "b"), frozenset({"a", "b"}))):
            self.assertEqual(approve(self.co, p), Generation(41, ("a", "b"), "a"))

    def test_stale_concurrent_refresh_never_replays(self):
        first = self.co.prepare(("a", "c"))
        second = self.co.prepare(("b", "a"))
        approve(self.co, first)
        with self.assertRaises(StaleGeneration):
            approve(self.co, second)
        self.assertEqual(self.co.state.pool, ("a", "c"))

    def test_forged_plan_cannot_select_unqualified_endpoint(self):
        correct = self.co.prepare(("a", "b"), frozenset({"b"}))
        fake = replace(correct, plan=replace(correct.plan,
                         action="switch_new_flows", selected="b"))
        with self.assertRaises(UnsafeActivation):
            approve(self.co, fake)
        self.assertEqual(self.co.state.number, 41)

    def test_forged_failed_list_or_candidate_rejected(self):
        p = self.co.prepare(("a", "b", "c"))
        for changed in (replace(p, failed=frozenset({"a"})),
                        replace(p, candidate=("b", "c")),
                        replace(p, candidate=("a", "a"))):
            with self.subTest(changed=changed):
                with self.assertRaises(UnsafeActivation):
                    approve(self.co, changed)
        self.assertEqual(self.co.state.number, 41)

    def test_external_mutable_inputs_snapshotted(self):
        candidate = ["a", "b", "c"]
        failed = {"c"}
        p = self.co.prepare(candidate, failed)
        candidate[:] = ["x"]
        failed.clear()
        s = approve(self.co, p)
        self.assertEqual(s.pool, ("a", "b"))
        self.assertEqual(s.active, "a")

    def test_concurrent_double_commit_has_one_winner(self):
        p = self.co.prepare(("b", "a", "c"))
        barrier = Barrier(3)
        outcomes = []
        def worker():
            barrier.wait()
            try:
                outcomes.append(("ok", approve(self.co, p).number))
            except StaleGeneration:
                outcomes.append(("stale", None))
        threads = [Thread(target=worker), Thread(target=worker)]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join(timeout=3)
            self.assertFalse(thread.is_alive())
        self.assertEqual(sorted(x[0] for x in outcomes), ["ok", "stale"])
        self.assertEqual(self.co.state.number, 42)

    def test_failed_api_or_continuity_does_not_promote(self):
        p = self.co.prepare(("b",))
        for args in (
            {"validated": False, "api_healthy": True, "continuity_verified": True},
            {"validated": True, "api_healthy": False, "continuity_verified": True},
            {"validated": True, "api_healthy": True, "continuity_verified": False},
        ):
            with self.subTest(args=args):
                with self.assertRaises(UnsafeActivation):
                    self.co.commit(p, **args)
                self.assertEqual(self.co.state, Generation(41, ("a", "b"), "a"))


if __name__ == "__main__":
    unittest.main()
