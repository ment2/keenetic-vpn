"""Disposable Linux process tests for v30 supervisor fencing (NOT router integration)."""
from contextlib import nullcontext
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from xray.staging import v30_supervisor_core as c


class SupervisorCoreSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.lock = self.root / "shared.lock"
        self.journal = self.root / "journal.json"

    def test_process_identity_contains_kernel_start_ticks_and_argv(self):
        ident = c.proc_identity(os.getpid())
        self.assertEqual(ident.pid, os.getpid())
        self.assertGreater(ident.start_ticks, 0)
        self.assertTrue(ident.argv)
        self.assertEqual(c.validate_identity(ident), ident)

    def test_invalid_pid_refused(self):
        with self.assertRaises(c.FenceError):
            c.proc_stat(1)

    def test_pid_start_ticks_mismatch_refused(self):
        ident = c.proc_identity(os.getpid())
        changed = c.Identity(ident.pid, ident.start_ticks + 1, ident.exe, ident.argv)
        with self.assertRaises(c.FenceError):
            c.validate_identity(changed)

    def test_process_executable_mismatch_refused(self):
        ident = c.proc_identity(os.getpid())
        changed = c.Identity(ident.pid, ident.start_ticks, "/different/binary", ident.argv)
        with self.assertRaises(c.FenceError):
            c.validate_identity(changed)

    def test_process_cmdline_mismatch_refused(self):
        ident = c.proc_identity(os.getpid())
        changed = c.Identity(ident.pid, ident.start_ticks, ident.exe, ("/wrong",))
        with self.assertRaises(c.FenceError):
            c.validate_identity(changed)

    def test_lock_private_inode_and_release(self):
        with c.supervisor_lock(self.lock):
            self.assertEqual(self.lock.stat().st_mode & 0o777, 0o600)
        with c.supervisor_lock(self.lock):
            pass

    def test_symlink_lock_refused(self):
        self.lock.symlink_to(self.root / "elsewhere")
        with self.assertRaisesRegex(c.FenceError, "symlink"):
            with c.supervisor_lock(self.lock):
                pass

    def test_existing_unsafe_mode_lock_refused(self):
        self.lock.write_text("")
        self.lock.chmod(0o666)
        with self.assertRaisesRegex(c.FenceError, "mode"):
            with c.supervisor_lock(self.lock):
                pass

    def test_cross_process_flock_denies_concurrent_entrypoint(self):
        # External child holds same lock inode while an unrelated controller
        # attempts a conflicting operation. No router processes/signals.
        script = (
            "import sys,time;from xray.staging.v30_supervisor_core import supervisor_lock;"
            "from pathlib import Path;"
            "with_dummy=1\n"
            "with supervisor_lock(Path(sys.argv[1]),timeout=3):\n"
            " print('LOCK_HELD',flush=True);time.sleep(1.2)\n"
        )
        child = subprocess.Popen([sys.executable, "-c", script, str(self.lock)],
             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(), "LOCK_HELD")
            with self.assertRaisesRegex(c.FenceError, "busy"):
                with c.supervisor_lock(self.lock, timeout=0.08):
                    pass
            child.wait(timeout=3)
            self.assertEqual(child.returncode, 0)
            with c.supervisor_lock(self.lock):
                pass
        finally:
            if child.poll() is None:
                child.terminate()
                child.wait(timeout=3)
            child.stdout.close()
            child.stderr.close()

    def test_crashed_holder_auto_unlocks_for_independent_recovery(self):
        script = (
            "import sys,time;from pathlib import Path;"
            "from xray.staging.v30_supervisor_core import supervisor_lock\n"
            "with supervisor_lock(Path(sys.argv[1])):\n"
            " print('HELD',flush=True);time.sleep(9)\n"
        )
        child = subprocess.Popen([sys.executable, "-c", script, str(self.lock)],
                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(), "HELD")
            child.kill()  # disposable lab child; no router PIDs
            child.wait(timeout=3)
            with c.supervisor_lock(self.lock, timeout=0.5):
                self.assertTrue(True)
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=3)
            child.stdout.close()
            child.stderr.close()

    def test_journal_fsync_and_private_mode(self):
        c.atomic_journal(self.journal, {"phase": "candidate_prepared", "pid": 123})
        self.assertEqual(json.loads(self.journal.read_text())["phase"], "candidate_prepared")
        self.assertEqual(self.journal.stat().st_mode & 0o777, 0o600)

    def test_atomic_numeric_pidfile_is_private(self):
        path = self.root / "xray-watchdog.pid"
        c.atomic_pidfile(path, 32713)
        self.assertEqual(path.read_text(), "32713\\n")
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        c.atomic_pidfile(path, 41234)
        self.assertEqual(path.read_text(), "41234\\n")

    def test_pidfile_symlink_refused(self):
        path = self.root / "xray-wifi.pid"
        path.symlink_to(self.root / "target")
        with self.assertRaisesRegex(c.FenceError, "symlink"):
            c.atomic_pidfile(path, 24097)

    def test_journal_symlink_refused(self):
        self.journal.symlink_to(self.root / "other")
        with self.assertRaisesRegex(c.FenceError, "symlink"):
            c.atomic_journal(self.journal, {"phase": "armed"})

    def test_gated_spawn_cannot_run_if_journal_fails(self):
        # The test child may inherit stdout/stderr only; it never receives
        # authorization byte if atomic write fails. No external service.
        with patch.object(c, "atomic_journal", side_effect=c.FenceError("fsync failed")):
            with self.assertRaisesRegex(c.FenceError, "fsync failed"):
                c.gated_spawn(sys.executable,
                    [sys.executable, "-c", "raise RuntimeError('SHOULD_NOT_EXEC')"],
                    self.journal)
        self.assertFalse(self.journal.exists())

    def test_gated_spawn_fsyncs_identity_before_child_exec(self):
        output = self.root / "child-marker"
        argv = [sys.executable, "-c",
                "from pathlib import Path;Path(%r).write_text('RUN')" % str(output)]
        with c.supervisor_lock(self.lock):
            pid, ticks = c.gated_spawn(sys.executable, argv, self.journal)
        record = json.loads(self.journal.read_text())
        self.assertEqual(record["pid"], pid)
        self.assertEqual(record["start_ticks"], ticks)
        self.assertEqual(record["phase"], "candidate_prepared")
        for _ in range(200):
            if output.exists():
                break
            time.sleep(0.01)
        self.assertTrue(output.exists())
        os.waitpid(pid, 0)

    def test_signal_has_no_unsafe_kill_fallback(self):
        fake = c.Identity(55555, 123, "/bin/fake", ("/bin/fake",))
        with patch.object(c, "validate_identity", side_effect=c.FenceError("identity drift")):
            with patch.object(c.os, "kill", side_effect=AssertionError("unsafe kill")):
                with self.assertRaises(c.FenceError):
                    c.scoped_signal(fake, signal.SIGTERM)

    def test_all_five_actors_must_use_one_lock(self):
        actors = ("S97", "S98", "watchdog", "cutover", "guardian")
        rows = [{"role": actor, "lock_path": str(self.lock), "requires_lock": True}
                for actor in actors]
        self.assertTrue(c.lock_contract_proof(rows, self.lock))
        for i in range(5):
            damaged = [dict(x) for x in rows]
            damaged[i]["lock_path"] = str(self.root / "other.lock")
            with self.assertRaises(c.FenceError):
                c.lock_contract_proof(damaged, self.lock)
        with self.assertRaises(c.FenceError):
            c.lock_contract_proof(rows[:-1], self.lock)

    def test_core_no_global_killall(self):
        source = Path(c.__file__).read_text(encoding="utf-8")
        self.assertNotIn("killall xray", source)
        self.assertNotIn("os.kill(", source)
        self.assertIn("pidfd_send_signal(", source)


if __name__ == "__main__":
    unittest.main()
