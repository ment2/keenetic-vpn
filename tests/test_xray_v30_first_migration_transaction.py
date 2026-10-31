"""Isolated first migration contract. No live PID signals or production calls."""
from dataclasses import fields, replace
from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

from xray.lab.v30_first_migration_transaction import (
    Evidence, Identity, Journal, Rejected, State, Transaction, preflight, synthetic_demo,
)


def known_good():
    kw = {f.name: True for f in fields(Evidence)
          if f.name not in ("old", "watchdog", "wifi_repair")}
    return Evidence(Identity(13546, 100216734),
                    Identity(32713, 61575997),
                    Identity(24097, 60711544), **kw)


class FirstMigrationTransactionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.e = known_good()
        self.journal = Journal(Path(self.tmp.name))
        self.t = Transaction(self.journal, self.e)

    def arm(self):
        return self.t.arm(self.t.s.generation, independent_guard_active=True,
                          rollback_timeout_seconds=60)

    def fence(self):
        return self.t.fence(self.t.s.generation,
                            watchdog_identity=self.e.watchdog,
                            wifi_identity=self.e.wifi_repair,
                            watchdog_stopped=True, wifi_stopped=True,
                            service_paths_fenced=True)

    def stop(self):
        return self.t.stop_legacy(self.t.s.generation, old_identity=self.e.old,
                                  no_competing_xray=True)

    def activate(self):
        return self.t.activate(self.t.s.generation, candidate=Identity(5555, 6789),
                               exclusive_tcp_and_udp=True)

    def verify(self):
        return self.t.verify(self.t.s.generation, **{
            k: True for k in ("api_ok", "socks_ok", "tproxy_tcp_ok", "tproxy_udp_ok",
                              "openai_via_vpn_ok", "dns_ipv6_no_leak_ok", "fail_closed_ok")
        })

    def test_default_preflight_required(self):
        e = Evidence(self.e.old, self.e.watchdog, self.e.wifi_repair)
        self.assertGreater(len(preflight(e)), 8)
        with self.assertRaises(Rejected):
            Transaction(self.journal, e)

    def test_all_evidence_independently_required(self):
        for f in fields(Evidence):
            if f.name in ("old", "watchdog", "wifi_repair"):
                continue
            with self.subTest(f=f.name):
                self.assertIn(f.name, preflight(replace(self.e, **{f.name: False})))

    def test_pid_identity_distinct(self):
        self.assertIn("distinct_process_identities", preflight(
            replace(self.e, watchdog=self.e.old)))

    def test_invalid_pid_and_ticks(self):
        with self.assertRaises(Rejected):
            Identity(1, 10)
        with self.assertRaises(Rejected):
            Identity(500, 0)

    def test_arm_requires_guard(self):
        with self.assertRaises(Rejected):
            self.t.arm(1, independent_guard_active=False, rollback_timeout_seconds=60)
        self.assertEqual(self.t.s.phase, "legacy")

    def test_arm_rollback_timeout_bounded(self):
        for seconds in (0, 29, 121, 900):
            with self.subTest(seconds=seconds), self.assertRaises(Rejected):
                self.t.arm(1, independent_guard_active=True,
                           rollback_timeout_seconds=seconds)

    def test_reject_stale_generation(self):
        with self.assertRaises(Rejected):
            self.t.arm(0, independent_guard_active=True, rollback_timeout_seconds=60)

    def test_arm_durable_to_disk(self):
        self.arm()
        self.assertEqual(self.journal.load().phase, "armed")
        self.assertEqual(self.journal.load().generation, 2)
        self.assertEqual(oct(self.journal.file.stat().st_mode & 0o777), "0o600")

    def test_reject_fence_before_guard(self):
        with self.assertRaises(Rejected):
            self.fence()

    def test_watchdog_pid_reuse_rejected(self):
        self.arm()
        with self.assertRaises(Rejected):
            self.t.fence(2, watchdog_identity=Identity(self.e.watchdog.pid, self.e.watchdog.start_ticks+1),
                         wifi_identity=self.e.wifi_repair, watchdog_stopped=True,
                         wifi_stopped=True, service_paths_fenced=True)

    def test_wifi_pid_reuse_rejected(self):
        self.arm()
        with self.assertRaises(Rejected):
            self.t.fence(2, watchdog_identity=self.e.watchdog,
                         wifi_identity=Identity(self.e.wifi_repair.pid, self.e.wifi_repair.start_ticks+1),
                         watchdog_stopped=True, wifi_stopped=True, service_paths_fenced=True)

    def test_watchdog_fence_missing(self):
        self.arm()
        with self.assertRaises(Rejected):
            self.t.fence(2, watchdog_identity=self.e.watchdog,
                         wifi_identity=self.e.wifi_repair, watchdog_stopped=False,
                         wifi_stopped=True, service_paths_fenced=True)

    def test_wifi_fence_missing(self):
        self.arm()
        with self.assertRaises(Rejected):
            self.t.fence(2, watchdog_identity=self.e.watchdog,
                         wifi_identity=self.e.wifi_repair, watchdog_stopped=True,
                         wifi_stopped=False, service_paths_fenced=True)

    def test_init_service_paths_must_be_fenced(self):
        self.arm()
        with self.assertRaises(Rejected):
            self.t.fence(2, watchdog_identity=self.e.watchdog,
                         wifi_identity=self.e.wifi_repair, watchdog_stopped=True,
                         wifi_stopped=True, service_paths_fenced=False)

    def test_stop_old_requires_fence(self):
        self.arm()
        with self.assertRaises(Rejected):
            self.stop()

    def test_stop_old_pid_reuse(self):
        self.arm(); self.fence()
        with self.assertRaises(Rejected):
            self.t.stop_legacy(3, old_identity=Identity(13546, 100216735),
                               no_competing_xray=True)

    def test_competing_xray_blocks_stop(self):
        self.arm(); self.fence()
        with self.assertRaises(Rejected):
            self.t.stop_legacy(3, old_identity=self.e.old,
                               no_competing_xray=False)

    def test_old_tcp_not_preserved_in_first_migration(self):
        self.arm(); self.fence(); self.stop()
        self.assertFalse(self.t.s.old_tcp_preserved)
        self.assertFalse(self.t.s.old_running)

    def test_activating_before_old_stop_rejected(self):
        self.arm(); self.fence()
        with self.assertRaises(Rejected):
            self.activate()

    def test_candidate_same_old_pid_rejected(self):
        self.arm(); self.fence(); self.stop()
        with self.assertRaises(Rejected):
            self.t.activate(4, candidate=self.e.old,
                            exclusive_tcp_and_udp=True)

    def test_candidate_requires_both_tcp_udp(self):
        self.arm(); self.fence(); self.stop()
        with self.assertRaises(Rejected):
            self.t.activate(4, candidate=Identity(5555, 6789),
                            exclusive_tcp_and_udp=False)

    def test_missing_any_gate_denies_success(self):
        required = ("api_ok", "socks_ok", "tproxy_tcp_ok", "tproxy_udp_ok",
                    "openai_via_vpn_ok", "dns_ipv6_no_leak_ok", "fail_closed_ok")
        self.arm(); self.fence(); self.stop(); self.activate()
        for bad in required:
            gates = {k: True for k in required}
            gates[bad] = False
            with self.subTest(bad=bad), self.assertRaises(Rejected):
                self.t.verify(self.t.s.generation, **gates)
            self.assertEqual(self.t.s.phase, "candidate_running")

    def test_crash_resume_then_autonomous_rollback(self):
        self.arm(); self.fence(); self.stop(); self.activate()
        saved = self.journal.load()
        self.assertEqual(saved.candidate, Identity(5555, 6789))
        fresh = Transaction.recover(self.journal, self.e)
        s = fresh.on_guard_timeout(fresh.s.generation,
                candidate_identity=Identity(5555, 6789),
                old_config_readback_ok=True, old_tcp_udp_bound=True,
                watchdog_unfenced=True, wifi_unfenced=True)
        self.assertEqual(s.phase, "restored")
        self.assertTrue(s.rollback_rebind_proven)
        self.assertFalse(s.guard_live)

    def test_guard_not_present_refuses_timeout(self):
        with self.assertRaises(Rejected):
            self.t.on_guard_timeout(1)

    def test_partial_rollback_is_blocked_not_restored(self):
        self.arm(); self.fence(); self.stop(); self.activate()
        s = self.t.on_guard_timeout(self.t.s.generation,
                 candidate_identity=Identity(5555, 6789),
                 old_config_readback_ok=True, old_tcp_udp_bound=False,
                 watchdog_unfenced=True, wifi_unfenced=True)
        self.assertEqual(s.phase, "blocked")
        self.assertFalse(s.rollback_rebind_proven)

    def test_rollback_rejects_candidate_identity_mismatch(self):
        self.arm(); self.fence(); self.stop(); self.activate()
        with self.assertRaises(Rejected):
            self.t.on_guard_timeout(self.t.s.generation,
                    candidate_identity=Identity(5555, 6790),
                    old_config_readback_ok=True, old_tcp_udp_bound=True,
                    watchdog_unfenced=True, wifi_unfenced=True)

    def test_finish_requires_new_supervisor_and_recovery(self):
        self.arm(); self.fence(); self.stop(); self.activate(); self.verify()
        for key in ("new_supervisor", "new_wifi_repair",
                    "boot_persistence", "auto_recovery"):
            kwargs = {k: True for k in ("new_supervisor", "new_wifi_repair",
                                        "boot_persistence", "auto_recovery")}
            kwargs[key] = False
            with self.subTest(key=key), self.assertRaises(Rejected):
                self.t.finish(self.t.s.generation, **kwargs)

    def test_dry_simulator_never_calls_process_signals(self):
        with patch("os.kill", side_effect=AssertionError("NO SIGNALS PERMITTED")):
            synthetic_demo()

    def test_journal_rejects_symlink(self):
        target = Path(self.tmp.name) / "outside.json"
        target.write_text("NONE")
        journal = Path(self.tmp.name) / "alias"
        journal.mkdir()
        (journal / "first-cutover-v30.json").symlink_to(target)
        with self.assertRaises(Rejected):
            Journal(journal)


if __name__ == "__main__":
    unittest.main()
