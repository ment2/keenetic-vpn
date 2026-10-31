"""Isolated pure/mock contracts for root-only staged Xray v30 broker.

No router calls, no service/kill signals, no firewall changes.
"""
from contextlib import contextmanager
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from xray.staging import v30_supervisor_service as svc
from xray.staging.v30_supervisor_core import FenceError, Identity


class DummyPaths:
    def __init__(self, root):
        self.run = root
        self.lock = root / "one-shared.lock"
        self.identity = root / "identity.json"
        self.prepared = root / "prepared.json"
        self.xray = Path(sys.executable).resolve()
        self.config = root / "config.json"


class XrayV30BrokerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.paths = DummyPaths(self.root)
        self.b = svc.Broker(self.paths, probe=lambda: True)
        self.pid = 5555
        self.identity = Identity(self.pid, 98765, str(self.paths.xray),
                                 self.b._expected_argv())

    def test_bootstrap_binds_existing_exact_pid_not_any_process(self):
        with patch.object(svc, "proc_identity", return_value=self.identity):
            with patch.object(self.b, "_all_xray", return_value=[self.pid]):
                self.assertEqual(self.b.bootstrap(self.pid, 98765),
                                 "BOUND_EXACT_LEGACY")
        state, pinned = self.b._load()
        self.assertEqual(state["phase"], "active")
        self.assertEqual(pinned, self.identity)
        self.assertEqual(self.paths.identity.stat().st_mode & 0o777, 0o600)

    def test_bootstrap_rejects_mismatched_start_ticks(self):
        with patch.object(svc, "proc_identity", return_value=self.identity):
            with self.assertRaises(FenceError):
                self.b.bootstrap(self.pid, 98766)
        self.assertFalse(self.paths.identity.exists())

    def test_bootstrap_rejects_competing_xray_pid(self):
        with patch.object(svc, "proc_identity", return_value=self.identity):
            with patch.object(self.b, "_all_xray", return_value=[self.pid, 2]):
                with self.assertRaises(FenceError):
                    self.b.bootstrap(self.pid, 98765)

    def test_uninitialized_legacy_cannot_restart(self):
        with self.assertRaisesRegex(FenceError, "missing/private"):
            self.b.control("restart")

    def test_control_operation_uses_shared_mutex(self):
        order = []
        @contextmanager
        def lock(path):
            self.assertEqual(path, self.paths.lock)
            order.append("lock-enter")
            yield
            order.append("lock-exit")
        def stopped():
            self.assertEqual(order[-1], "lock-enter")
            order.append("stop")
        def started():
            self.assertEqual(order[-1], "stop")
            order.append("start")
            return "started"
        with patch.object(svc, "supervisor_lock", side_effect=lock):
            with patch.object(self.b, "_stop_under_lock", side_effect=stopped):
                with patch.object(self.b, "_start_under_lock", side_effect=started):
                    self.assertEqual(self.b.control("restart"), "started")
        self.assertEqual(order, ["lock-enter", "stop", "start", "lock-exit"])

    def test_watchdog_healthy_checks_identity_and_never_signals(self):
        with patch.object(self.b, "_load", return_value=({"phase": "active"}, self.identity)):
            with patch.object(self.b, "_verified_active",
                              return_value=({"phase": "active"}, self.identity)):
                with patch.object(svc, "scoped_signal",
                                  side_effect=AssertionError("must not signal")):
                    self.assertEqual(self.b.control("watchdog-once"),
                                     "HEALTHY_EXACT_XRAY")

    def test_watchdog_unknown_competing_process_refuses(self):
        with patch.object(self.b, "_load", return_value=({"phase": "active"}, self.identity)):
            with patch.object(self.b, "_verified_active",
                              side_effect=FenceError("PID drift")):
                with patch.object(self.b, "_all_xray", return_value=[99]):
                    with self.assertRaisesRegex(FenceError, "drift"):
                        self.b.control("watchdog-once")

    def test_addressed_stop_calls_only_scoped_signal(self):
        state={"schema":1, "phase":"active", "identity":{"pid":self.identity.pid, "start_ticks":self.identity.start_ticks, "exe":self.identity.exe, "argv":list(self.identity.argv)}}
        with patch.object(self.b, "_verified_active", return_value=(state, self.identity)):
            with patch.object(svc, "scoped_signal") as addressed:
                with patch.object(svc, "proc_identity", side_effect=FenceError("gone")):
                    with patch.object(self.b, "_all_xray", return_value=[]):
                        with patch.object(self.b, "probe", return_value=False):
                            self.assertEqual(self.b._stop_under_lock(),
                                             "EXACT_XRAY_STOPPED")
        addressed.assert_called_once_with(self.identity, svc.signal.SIGTERM)
        saved,_=self.b._load()
        self.assertEqual(saved["phase"], "stopped")

    def test_stop_unknown_port_refuses_to_claim_stopped(self):
        with patch.object(self.b, "_verified_active", return_value=(
                {"schema":1,"phase":"active","identity":self.identity},
                self.identity)):
            with patch.object(svc, "scoped_signal"):
                with patch.object(svc, "proc_identity", side_effect=FenceError("gone")):
                    with patch.object(self.b, "_all_xray", return_value=[]):
                        with self.assertRaises(FenceError):
                            self.b._stop_under_lock()

    def test_stopped_journal_does_not_start_if_unknown_xray_exists(self):
        from xray.staging.v30_supervisor_core import atomic_journal
        atomic_journal(self.paths.identity, {
            "schema":1, "phase":"stopped",
            "identity":{"pid":self.pid,"start_ticks":98765,
                        "exe":self.identity.exe,
                        "argv":list(self.identity.argv)}})
        with patch.object(self.b, "_all_xray", return_value=[42]):
            with self.assertRaisesRegex(FenceError, "unknown"):
                self.b.control("start")

    def test_wifi_actor_refuses_unsafe_kernel_without_any_rewrite(self):
        with patch.object(self.b, "_wifi_check_under_lock", return_value=False):
            with patch.object(self.b, "_failclosed_kernel_under_lock",
                              side_effect=FenceError("no kill switch")):
                with patch.object(self.b, "run",
                                  side_effect=AssertionError("must not mutate kernel")):
                    with self.assertRaisesRegex(FenceError, "no kill switch"):
                        self.b.wifi_once()
        self.assertEqual(self.paths.lock.stat().st_mode & 0o777, 0o600)

    def test_wifi_repair_mangle_write_requires_preserved_fail_closed(self):
        self.b.run = lambda cmd: (
            "-P FORWARD DROP\n-A FORWARD -j XRAY_KS_HOME" if cmd[-1]=="FORWARD" else
            "-A XRAY_KS_HOME -i br0 -j DROP" if cmd[-1]=="XRAY_KS_HOME" else
            "-P FORWARD DROP")
        self.b._failclosed_kernel_under_lock()

    def test_wifi_repair_simulates_tcp_udp_with_shared_lock(self):
        seen=[]
        def run(cmd):
            seen.append(cmd)
            if cmd[-1] == "FORWARD" and "-S" in cmd:
                return "-P FORWARD DROP\n-A FORWARD -j XRAY_KS_HOME"
            if cmd[-1] == "XRAY_KS_HOME" and "-S" in cmd:
                return "-A XRAY_KS_HOME -i br0 -j DROP"
            if cmd[-1] == "XRAY_WIFI" and "-S" in cmd:
                return "-A XRAY_WIFI -p tcp -j TPROXY --on-port 12345\n-A XRAY_WIFI -p udp -j TPROXY --on-port 12345"
            if cmd == ["ip","route","show","table","100"]:
                return "local default dev lo table 100"
            if cmd == ["ip","rule","show"]:
                return "20000: fwmark 0x40000000/0x40000000 lookup 100"
            return ""
        self.b.run=run
        self.assertEqual(self.b.wifi_once(force_repair=True),
                         "WIFI_REPAIRED_UNDER_SHARED_MUTEX")
        self.assertTrue(any("--on-port" in cmd and "tcp" in cmd for cmd in seen))
        self.assertTrue(any("--on-port" in cmd and "udp" in cmd for cmd in seen))
        self.assertTrue(any("-F" in cmd and "XRAY_WIFI" in cmd for cmd in seen))

    def test_wifi_missing_killswitch_fails_before_rule_writes(self):
        seen=[]
        def run(cmd):
            seen.append(cmd)
            if "-S" in cmd:
                return "-A FORWARD -j ACCEPT"
            raise AssertionError("MUTATING_OPERATION_NOT_ALLOWED")
        self.b.run=run
        with self.assertRaisesRegex(FenceError, "failclosed kernel"):
            self.b.wifi_once(force_repair=True)
        self.assertTrue(all("-S" in cmd for cmd in seen))

    def test_wifi_healthy_does_not_rewrite_kernel(self):
        with patch.object(self.b, "_wifi_check_under_lock", return_value=True):
            with patch.object(self.b, "run",
                              side_effect=AssertionError("must not mutate kernel")):
                self.assertEqual(self.b.wifi_once(), "WIFI_TPROXY_HEALTHY")

    def test_watchdog_bootstrap_requires_exact_legacy_pid_and_ticks(self):
        from xray.staging.v30_supervisor_core import atomic_pidfile
        old = Identity(self.pid, 98765, str(self.paths.xray),
                       ("/opt/bin/xray-watchdog.sh",))
        atomic_pidfile(self.b._actor_pidfile("watchdog"), self.pid)
        with patch.object(svc, "proc_identity", return_value=old):
            self.assertEqual(self.b.actor_bootstrap("watchdog", self.pid, 98765),
                             "ACTOR_LEGACY_PINNED")
        active, observed = self.b._actor_load("watchdog")
        self.assertTrue(active["legacy"])
        self.assertEqual(observed, old)
        with patch.object(svc, "proc_identity", return_value=old):
            with self.assertRaises(FenceError):
                self.b.actor_bootstrap("watchdog", self.pid, 98765)

    def test_watchdog_scoped_stop_updates_compatibility_pidfile(self):
        from xray.staging.v30_supervisor_core import atomic_journal, atomic_pidfile
        old = Identity(self.pid, 98765, str(self.paths.xray),
                       ("/opt/bin/xray-watchdog.sh",))
        atomic_pidfile(self.b._actor_pidfile("watchdog"), self.pid)
        atomic_journal(self.b._actor_path("watchdog"), {
            "schema":1, "phase":"active", "identity":{
                "pid":old.pid, "start_ticks":old.start_ticks,
                "exe":old.exe, "argv":list(old.argv)}, "legacy":True})
        with patch.object(svc, "proc_identity", side_effect=[
                old, FenceError("stopped")]):
            with patch.object(svc, "scoped_signal") as scoped:
                self.assertEqual(self.b.actor_control("watchdog", "stop"),
                                 "ACTOR_STOPPED_EXACT_IDENTITY")
        scoped.assert_called_once_with(old, svc.signal.SIGTERM)
        self.assertFalse(self.b._actor_pidfile("watchdog").exists())
        self.assertEqual(self.b._actor_load("watchdog")[0]["phase"], "stopped")

    def test_actor_start_requires_fully_cleared_old_pid_and_prepared_state(self):
        from xray.staging.v30_supervisor_core import atomic_journal
        old = Identity(self.pid, 98765, str(self.paths.xray),
                       ("/opt/bin/xray-watchdog.sh",))
        atomic_journal(self.b._actor_path("watchdog"), {
            "schema":1, "phase":"stopped", "identity":{
                "pid":old.pid, "start_ticks":old.start_ticks,
                "exe":old.exe, "argv":list(old.argv)}, "legacy":True})
        self.b._actor_prepared("watchdog").write_text("UNRECONCILED")
        with patch.object(svc, "gated_spawn",
                          side_effect=AssertionError("must not spawn")):
            with self.assertRaisesRegex(FenceError, "unreconciled"):
                self.b.actor_control("watchdog", "start")

    def test_new_watchdog_gated_spawn_has_durable_pid_and_compatibility_file(self):
        from xray.staging.v30_supervisor_core import atomic_journal
        old = Identity(self.pid, 98765, str(self.paths.xray),
                       ("/opt/bin/xray-watchdog.sh",))
        atomic_journal(self.b._actor_path("watchdog"), {
            "schema":1, "phase":"stopped", "identity":{
                "pid":old.pid, "start_ticks":old.start_ticks,
                "exe":old.exe, "argv":list(old.argv)}, "legacy":True})
        argv=self.b._actor_expected_cmd("watchdog")
        new=Identity(7777, 3333, str(Path(sys.executable).resolve()), argv)
        def spawn(exe, args, journal):
            self.assertEqual(tuple(args), argv)
            Path(journal).write_text("PREPARED")
            return 7777, 3333
        with patch.object(svc, "gated_spawn", side_effect=spawn):
            with patch.object(svc, "proc_identity", return_value=new):
                self.assertEqual(self.b.actor_control("watchdog", "start"),
                                 "ACTOR_STARTED_WITH_DURABLE_PID_TICKS")
        self.assertEqual(self.b._actor_pidfile("watchdog").read_text().strip(), "7777")
        self.assertEqual(self.b._actor_load("watchdog")[1], new)
        self.assertFalse(self.b._actor_prepared("watchdog").exists())

    def test_source_has_no_global_killall_or_unguarded_cli_retry(self):
        source = Path(svc.__file__).read_text(encoding="utf-8")
        self.assertNotIn("killall xray", source)
        self.assertNotIn("os.kill(", source)
        self.assertIn("scoped_signal(old, signal.SIGTERM)", source)
        self.assertIn("with supervisor_lock(self.p.lock)", source)
        self.assertIn("_failclosed_kernel_under_lock", source)


if __name__ == "__main__":
    unittest.main()
