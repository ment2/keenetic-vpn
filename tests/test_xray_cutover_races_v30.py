"""Deterministic simulated watchdog and concurrent-controller races.

No production watchdog or router process is launched.
"""
import tempfile
import threading
import unittest
from xray.lab.cutover_controller_v30 import CutoverError, FakeProcess, Lab


class RaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.lab = Lab(self.tmp.name, FakeProcess(1001, 10), FakeProcess(1002, 20))

    def test_watchdog_observes_fence_during_prepared_and_switched(self):
        seen = []
        original = self.lab.record

        def capture(phase):
            original(phase)
            seen.append((phase, self.lab.watchdog_fenced))
        self.lab.record = capture
        self.lab.cutover(expected_generation=1, old_identity=(1001, 10),
                         candidate_identity=(1002, 20), handoff_proven=True)
        self.assertEqual(seen, [("prepared", True), ("switched", True), ("verified", True)])

    def test_failed_cutover_unfences_only_after_old_owner_restored(self):
        states = []
        original = self.lab.record

        def capture(phase):
            original(phase)
            states.append((phase, self.lab.owner, self.lab.watchdog_fenced))
        self.lab.record = capture
        with self.assertRaises(CutoverError):
            self.lab.cutover(expected_generation=1, old_identity=(1001, 10),
                             candidate_identity=(1002, 20), handoff_proven=True,
                             fault="crash_post_switch")
        self.assertEqual(states[-1], ("rolled_back", "old", False))

    def test_second_controller_rejected_during_locked_transaction(self):
        errors = []
        with self.lab.locked():
            def contender():
                try:
                    self.lab.cutover(expected_generation=1, old_identity=(1001, 10),
                                     candidate_identity=(1002, 20), handoff_proven=True)
                except CutoverError as exc:
                    errors.append(str(exc))
            t = threading.Thread(target=contender)
            t.start()
            t.join(timeout=3)
            self.assertFalse(t.is_alive())
        self.assertEqual(len(errors), 1)
        self.assertIn("lock", errors[0])

    def test_dead_old_process_blocks_safe_rollback(self):
        self.lab.cutover(expected_generation=1, old_identity=(1001, 10),
                         candidate_identity=(1002, 20), handoff_proven=True)
        self.lab.old.alive = False
        self.lab.rollback(expected_generation=2)
        self.assertEqual(self.lab.owner, "blocked")
        self.assertTrue(self.lab.watchdog_fenced)


if __name__ == "__main__":
    unittest.main()
