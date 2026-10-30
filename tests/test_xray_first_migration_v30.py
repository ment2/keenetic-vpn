"""Offline migration fault injection, no sockets, router or Xray process."""
import unittest
from dataclasses import replace
from xray.lab.first_migration_model_v30 import (
    State, MigrationRejected, invariant, prepare, cutover, finish,
    rollback, watchdog_action,
)


class FirstMigrationTests(unittest.TestCase):
    def setUp(self):
        self.old = State(active_tcp=3)

    def prepared(self):
        return prepare(self.old, expected_generation=0, validated=True,
                       api_healthy=True, watchdog_fenced=True)

    def draining(self):
        return cutover(self.prepared(), expected_generation=0,
                       ingress_handoff_proven=True)

    def test_prepare_does_not_move_ingress_or_kill_old(self):
        s = self.prepared()
        self.assertEqual((s.ingress_owner, s.legacy_alive, s.phase),
                         ("legacy", True, "prepared"))

    def test_bad_candidate_rejected(self):
        with self.assertRaises(MigrationRejected):
            prepare(self.old, expected_generation=0, validated=False,
                    api_healthy=True, watchdog_fenced=True)

    def test_api_failure_rejected(self):
        with self.assertRaises(MigrationRejected):
            prepare(self.old, expected_generation=0, validated=True,
                    api_healthy=False, watchdog_fenced=True)

    def test_watchdog_must_be_fenced(self):
        with self.assertRaises(MigrationRejected):
            prepare(self.old, expected_generation=0, validated=True,
                    api_healthy=True, watchdog_fenced=False)

    def test_stale_generation_rejected(self):
        with self.assertRaises(MigrationRejected):
            prepare(self.old, expected_generation=99, validated=True,
                    api_healthy=True, watchdog_fenced=True)

    def test_cutover_requires_proven_handoff(self):
        with self.assertRaises(MigrationRejected):
            cutover(self.prepared(), expected_generation=0,
                    ingress_handoff_proven=False)

    def test_cutover_keeps_legacy_alive_for_drain(self):
        s = self.draining()
        self.assertEqual((s.ingress_owner, s.legacy_alive, s.generation),
                         ("candidate", True, 1))

    def test_cannot_finish_with_active_old_tcp(self):
        with self.assertRaises(MigrationRejected):
            finish(self.draining(), old_tcp_drained=False,
                   candidate_healthy=True)

    def test_cannot_finish_if_candidate_unhealthy(self):
        with self.assertRaises(MigrationRejected):
            finish(replace(self.draining(), active_tcp=0),
                   old_tcp_drained=True, candidate_healthy=False)

    def test_finish_after_drain(self):
        s = finish(replace(self.draining(), active_tcp=0),
                   old_tcp_drained=True, candidate_healthy=True)
        self.assertEqual((s.phase, s.legacy_alive, s.ingress_owner),
                         ("api_enabled", False, "candidate"))

    def test_rollback_prepared_restores_legacy(self):
        s = rollback(self.prepared(), legacy_healthy=True)
        self.assertEqual((s.phase, s.ingress_owner, s.candidate_alive),
                         ("legacy", "legacy", False))

    def test_rollback_draining_restores_legacy(self):
        s = rollback(self.draining(), legacy_healthy=True)
        self.assertEqual((s.phase, s.ingress_owner, s.generation),
                         ("legacy", "legacy", 2))

    def test_rollback_unhealthy_legacy_rejected(self):
        with self.assertRaises(MigrationRejected):
            rollback(self.draining(), legacy_healthy=False)

    def test_fenced_watchdog_never_restarts(self):
        self.assertEqual(watchdog_action(self.draining(),
                                        socks_listener_healthy=False),
                         "alert_only")

    def test_unfenced_watchdog_does_not_killall(self):
        self.assertEqual(watchdog_action(self.old,
                                        socks_listener_healthy=False),
                         "requires_explicit_recovery")

    def test_direct_fallback_rejected(self):
        with self.assertRaises(MigrationRejected):
            invariant(replace(self.old, direct_fallback=True))

    def test_killswitch_loss_rejected(self):
        with self.assertRaises(MigrationRejected):
            invariant(replace(self.old, kill_switch=False))

    def test_dead_ingress_owner_rejected(self):
        with self.assertRaises(MigrationRejected):
            invariant(replace(self.old, legacy_alive=False))

    def test_double_cutover_rejected(self):
        with self.assertRaises(MigrationRejected):
            cutover(self.draining(), expected_generation=0,
                    ingress_handoff_proven=True)

    def test_old_tcp_never_claimed_migrated(self):
        s = self.draining()
        self.assertEqual(s.active_tcp, 3)
        self.assertTrue(s.legacy_alive)


if __name__ == "__main__":
    unittest.main()
