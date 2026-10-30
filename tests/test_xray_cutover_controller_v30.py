"""Fault-injection tests of fake lab only; no network, router, or Xray binary."""
import fcntl
import json
import tempfile
import unittest
from pathlib import Path
from xray.lab.cutover_controller_v30 import CutoverError, FakeProcess, Lab


class CutoverLabTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.lab = Lab(self.tmp.name, FakeProcess(1001, 101), FakeProcess(1002, 202))

    def go(self, **kw):
        return self.lab.cutover(expected_generation=1, old_identity=(1001, 101),
                                candidate_identity=(1002, 202), **kw)

    def test_default_cannot_cutover_without_real_handoff(self):
        with self.assertRaisesRegex(CutoverError, "NOT proven"):
            self.go()
        self.assertEqual(self.lab.owner, "old")

    def test_successful_synthetic_handoff_keeps_old_alive(self):
        self.assertEqual(self.go(handoff_proven=True), "SWITCHED_SIMULATION_ONLY")
        self.assertTrue(self.lab.old.alive)
        self.assertEqual(self.lab.owner, "candidate")
        self.assertEqual(self.lab.events, ["prepared", "switched", "verified"])

    def test_pre_switch_fault_rolls_back(self):
        with self.assertRaises(CutoverError):
            self.go(handoff_proven=True, fault="crash_pre_switch")
        self.assertEqual(self.lab.owner, "old")
        self.assertEqual(self.lab.events, ["prepared", "rolled_back"])

    def test_post_switch_fault_rolls_back(self):
        with self.assertRaises(CutoverError):
            self.go(handoff_proven=True, fault="crash_post_switch")
        self.assertEqual(self.lab.owner, "old")
        self.assertEqual(self.lab.events[-1], "rolled_back")

    def test_stale_generation_rejected(self):
        with self.assertRaisesRegex(CutoverError, "stale generation"):
            self.lab.cutover(expected_generation=0, old_identity=(1001, 101),
                             candidate_identity=(1002, 202), handoff_proven=True)

    def test_pid_reuse_old_rejected(self):
        with self.assertRaisesRegex(CutoverError, "old PID/start-ticks"):
            self.lab.cutover(expected_generation=1, old_identity=(1001, 99),
                             candidate_identity=(1002, 202), handoff_proven=True)

    def test_pid_reuse_candidate_rejected(self):
        with self.assertRaisesRegex(CutoverError, "candidate PID/start-ticks"):
            self.lab.cutover(expected_generation=1, old_identity=(1001, 101),
                             candidate_identity=(1002, 999), handoff_proven=True)

    def test_candidate_socks_not_ready_rejected(self):
        self.lab.candidate.socks_ready = False
        with self.assertRaisesRegex(CutoverError, "readiness"):
            self.go(handoff_proven=True)

    def test_candidate_tproxy_not_ready_rejected(self):
        self.lab.candidate.tproxy_ready = False
        with self.assertRaisesRegex(CutoverError, "readiness"):
            self.go(handoff_proven=True)

    def test_candidate_api_not_ready_rejected(self):
        self.lab.candidate.api_ready = False
        with self.assertRaisesRegex(CutoverError, "readiness"):
            self.go(handoff_proven=True)

    def test_kill_switch_loss_blocks(self):
        self.lab.kill_switch = False
        with self.assertRaisesRegex(CutoverError, "fail-closed"):
            self.go(handoff_proven=True)

    def test_direct_fallback_blocks(self):
        self.lab.direct_fallback = True
        with self.assertRaisesRegex(CutoverError, "fail-closed"):
            self.go(handoff_proven=True)

    def test_lock_contention_rejected(self):
        with self.lab.lock_path.open("a+") as f:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                with self.assertRaisesRegex(CutoverError, "lock"):
                    self.go(handoff_proven=True)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    def test_rollback_rejects_stale_generation(self):
        self.go(handoff_proven=True)
        with self.assertRaisesRegex(CutoverError, "stale rollback"):
            self.lab.rollback(expected_generation=1)

    def test_rollback_restores_old(self):
        self.go(handoff_proven=True)
        self.lab.rollback(expected_generation=2)
        self.assertEqual(self.lab.owner, "old")
        self.assertFalse(self.lab.watchdog_fenced)

    def test_unhealthy_old_rolls_back_to_blocked(self):
        self.go(handoff_proven=True)
        self.lab.old.alive = False
        self.lab.rollback(expected_generation=2)
        self.assertEqual(self.lab.owner, "blocked")
        self.assertTrue(self.lab.kill_switch)
        self.assertFalse(self.lab.direct_fallback)

    def test_journal_records_pid_start_ticks(self):
        self.go(handoff_proven=True)
        data = json.loads(self.lab.journal.read_text())
        self.assertEqual((data["old_pid"], data["old_start_ticks"]), (1001, 101))
        self.assertEqual(data["phase"], "verified")

    def test_recovery_of_switched_state(self):
        self.lab.owner = "candidate"
        self.lab.generation = 2
        self.lab.watchdog_fenced = True
        self.lab.record("switched")
        self.assertEqual(self.lab.recover(), "RECOVERED_SIMULATION_ONLY")
        self.assertEqual(self.lab.owner, "old")

    def test_recovery_rejects_pid_reuse(self):
        self.lab.record("prepared")
        self.lab.old.start_ticks = 999
        with self.assertRaisesRegex(CutoverError, "identity changed"):
            self.lab.recover()

    def test_recovery_verified_is_noop(self):
        self.go(handoff_proven=True)
        self.assertEqual(self.lab.recover(), "NO_RECOVERY_REQUIRED")

    def test_old_tcp_is_not_claimed_transferred(self):
        self.lab.active_old_tcp = 9
        self.go(handoff_proven=True)
        self.assertEqual(self.lab.active_old_tcp, 9)
        self.assertTrue(self.lab.old.alive)


if __name__ == "__main__":
    unittest.main()
