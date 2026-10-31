"""Deterministic read-only watchdog race / operator escalation contracts."""
import unittest
from dataclasses import replace
from xray.lab.watchdog_policy_v30 import Identity, Observation, decide


class WatchdogPolicyTests(unittest.TestCase):
    def setUp(self):
        self.ok = Observation(expected=Identity(13546, 100216734),
                              observed=Identity(13546, 100216734))

    def assert_action(self, obs, action):
        result = decide(obs)
        self.assertEqual(result.action, action)
        self.assertFalse(result.sends_signal)
        self.assertFalse(result.changes_routes)

    def test_healthy(self):
        self.assert_action(self.ok, "healthy")

    def test_missing_old_pid_no_auto_restart(self):
        self.assert_action(replace(self.ok, observed=None), "request_operator_recovery")

    def test_pid_reuse(self):
        self.assert_action(replace(self.ok, observed=Identity(13546, 100216735)), "block_new_flows")

    def test_pid_change(self):
        self.assert_action(replace(self.ok, observed=Identity(13547, 100216734)), "block_new_flows")

    def test_watchdog_fence(self):
        self.assert_action(replace(self.ok, watchdog_fenced=True), "observe_only")

    def test_transaction_lock(self):
        self.assert_action(replace(self.ok, lock_held=True), "observe_only")

    def test_prepared_does_not_restart(self):
        self.assert_action(replace(self.ok, phase="prepared", socks_ready=False), "observe_only")

    def test_switched_does_not_restart(self):
        self.assert_action(replace(self.ok, phase="switched", tproxy_udp_ready=False), "observe_only")

    def test_rollback_does_not_restart(self):
        self.assert_action(replace(self.ok, phase="rollback", observed=None), "observe_only")

    def test_missing_socks(self):
        self.assert_action(replace(self.ok, socks_ready=False), "request_operator_recovery")

    def test_missing_tproxy_tcp(self):
        self.assert_action(replace(self.ok, tproxy_tcp_ready=False), "request_operator_recovery")

    def test_missing_tproxy_udp(self):
        self.assert_action(replace(self.ok, tproxy_udp_ready=False), "request_operator_recovery")

    def test_killswitch_violation(self):
        self.assert_action(replace(self.ok, kill_switch_verified=False), "block_new_flows")

    def test_direct_fallback_violation(self):
        self.assert_action(replace(self.ok, direct_fallback=True), "block_new_flows")

    def test_generation_mismatch(self):
        self.assert_action(replace(self.ok, generation_matches=False), "block_new_flows")

    def test_invalid_journal(self):
        self.assert_action(replace(self.ok, journal_valid=False), "block_new_flows")

    def test_invalid_phase(self):
        self.assert_action(replace(self.ok, phase="unknown"), "block_new_flows")

    def test_invalid_process_identity(self):
        with self.assertRaises(ValueError):
            Identity(1, 0)

    def test_protocol_missing_cannot_be_healthy(self):
        for key in ("socks_ready", "tproxy_tcp_ready", "tproxy_udp_ready"):
            self.assertNotEqual(decide(replace(self.ok, **{key: False})).action, "healthy")


if __name__ == "__main__":
    unittest.main()
