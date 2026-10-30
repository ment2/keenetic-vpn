"""Offline generation CAS/fail-closed gate tests, no router interaction."""
import unittest
from xray.lab.pool_generation_v30 import (
    Coordinator, Generation, StaleGeneration, UnsafeActivation,
)


class GenerationTests(unittest.TestCase):
    def setUp(self):
        self.co = Coordinator(Generation(7, ("a", "b"), "a"))

    def test_reorder_retains_active(self):
        p = self.co.prepare(("b", "a"))
        state = self.co.commit(p, validated=True, api_healthy=True,
                               continuity_verified=True)
        self.assertEqual((state.number, state.active), (8, "a"))

    def test_new_standby_does_not_switch(self):
        p = self.co.prepare(("a", "b", "c"))
        state = self.co.commit(p, validated=True, api_healthy=True,
                               continuity_verified=True)
        self.assertEqual(state.active, "a")

    def test_failed_active_switches(self):
        p = self.co.prepare(("a", "b"), frozenset({"a"}))
        state = self.co.commit(p, validated=True, api_healthy=True,
                               continuity_verified=True)
        self.assertEqual(state.active, "b")

    def test_empty_candidate_never_commits(self):
        p = self.co.prepare(())
        state = self.co.commit(p, validated=True, api_healthy=True,
                               continuity_verified=True)
        self.assertEqual(state, Generation(7, ("a", "b"), "a"))

    def test_failed_validation_blocks_commit(self):
        p = self.co.prepare(("a", "b", "c"))
        with self.assertRaises(UnsafeActivation):
            self.co.commit(p, validated=False, api_healthy=True,
                           continuity_verified=True)
        self.assertEqual(self.co.state.number, 7)

    def test_api_failure_blocks_commit(self):
        p = self.co.prepare(("b",))
        with self.assertRaises(UnsafeActivation):
            self.co.commit(p, validated=True, api_healthy=False,
                           continuity_verified=True)

    def test_continuity_failure_blocks_commit(self):
        p = self.co.prepare(("b",))
        with self.assertRaises(UnsafeActivation):
            self.co.commit(p, validated=True, api_healthy=True,
                           continuity_verified=False)

    def test_stale_generation_cannot_commit(self):
        p1 = self.co.prepare(("a", "b", "c"))
        p2 = self.co.prepare(("a", "b", "d"))
        self.co.commit(p1, validated=True, api_healthy=True,
                       continuity_verified=True)
        with self.assertRaises(StaleGeneration):
            self.co.commit(p2, validated=True, api_healthy=True,
                           continuity_verified=True)
        self.assertEqual(self.co.state.pool, ("a", "b", "c"))

    def test_stale_generation_rejected_even_when_other_gates_fail(self):
        p = self.co.prepare(("b",))
        self.co.state = Generation(8, ("a", "b"), "a")
        with self.assertRaises(StaleGeneration):
            self.co.commit(p, validated=False, api_healthy=False,
                           continuity_verified=False)


if __name__ == "__main__":
    unittest.main()
