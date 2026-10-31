"""RC11 disposable process identity regression tests; never touch production."""
import os
import signal
import subprocess
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "xray" / "lab"))
from rc11_pidfd_guard import guarded_signal, start_ticks


class PidfdIdentityTests(unittest.TestCase):
    def setUp(self):
        self.child = subprocess.Popen(["sleep", "60"])
        self.ticks = start_ticks(self.child.pid)

    def tearDown(self):
        if self.child.poll() is None:
            self.child.terminate()
        self.child.wait(timeout=5)

    def test_wrong_start_ticks_cannot_signal(self):
        self.assertFalse(guarded_signal(self.child.pid, self.ticks + 1, signal.SIGTERM, "sleep"))
        self.assertIsNone(self.child.poll())

    def test_wrong_cmdline_cannot_signal(self):
        self.assertFalse(guarded_signal(self.child.pid, self.ticks, signal.SIGTERM, "not_the_child"))
        self.assertIsNone(self.child.poll())

    def test_unpinned_pid_rejected(self):
        self.assertFalse(guarded_signal(self.child.pid, 0, signal.SIGTERM, "sleep"))
        self.assertIsNone(self.child.poll())

    @unittest.skipUnless(hasattr(os, "pidfd_open") and hasattr(signal, "pidfd_send_signal"), "pidfd not supported")
    def test_actual_pidfd_signal(self):
        self.assertTrue(guarded_signal(self.child.pid, self.ticks, signal.SIGTERM, "sleep"))
        self.child.wait(timeout=5)
        self.assertIsNotNone(self.child.returncode)

    def test_stale_exit_pid_rejected(self):
        self.child.terminate()
        self.child.wait(timeout=5)
        self.assertFalse(guarded_signal(self.child.pid, self.ticks, signal.SIGTERM, "sleep"))


if __name__ == "__main__":
    unittest.main()
