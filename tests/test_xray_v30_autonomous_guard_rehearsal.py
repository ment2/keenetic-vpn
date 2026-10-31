"""Isolated detached autonomous-guard rehearsal. Never touches router."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from xray.lab.v30_autonomous_guard_rehearsal import stage, verify, guard
from xray.lab.v30_first_migration_transaction import Journal, Rejected


class AutonomousGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="v30-guardian-tests-")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)

    def test_independent_detached_process_can_recover(self):
        stage(self.path, simulate_restore=True)
        verify(self.path, simulate_restore=True)
        self.assertEqual(Journal(self.path).load().phase, "restored")

    def test_unproven_rollback_never_declared_restored(self):
        stage(self.path, simulate_restore=False)
        verify(self.path, simulate_restore=False)
        self.assertEqual(Journal(self.path).load().phase, "blocked")

    def test_guard_rejects_missing_journal(self):
        with self.assertRaises(FileNotFoundError):
            guard(self.path, delay=0, simulate_restore=True)

    def test_guard_rejects_unarmed_legacy_phase(self):
        from xray.lab.v30_first_migration_transaction import State
        Journal(self.path).save(State())
        with self.assertRaises(Rejected):
            guard(self.path, delay=0, simulate_restore=True)

    def test_stage_rejects_production_paths(self):
        with self.assertRaises(Rejected):
            stage(Path("/opt/var/run/xray-v30-fake"), simulate_restore=True)

    def test_selfcontained_cli_separate_processes(self):
        p = subprocess.run([sys.executable, "-m", "xray.lab.v30_autonomous_guard_rehearsal",
                            "--stage", str(self.path)], capture_output=True, text=True, timeout=5)
        self.assertEqual(p.returncode, 0, p.stderr)
        p = subprocess.run([sys.executable, "-m", "xray.lab.v30_autonomous_guard_rehearsal",
                            "--verify", str(self.path)], capture_output=True, text=True, timeout=8)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("independent detached guard recovered journal", p.stdout)


if __name__ == "__main__":
    unittest.main()
