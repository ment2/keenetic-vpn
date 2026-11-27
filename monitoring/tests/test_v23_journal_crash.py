"""Real SIGKILL and fsync tests in disposable directories; not power-loss proof."""
import importlib.util
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest

SOURCE=Path(__file__).parent/"fixtures/v23_journal_model.py"
spec=importlib.util.spec_from_file_location("journal_model",SOURCE)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class JournalCrashTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="v23-journal-fixture-")
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/"marker").write_bytes(b"synthetic-only")
        for k,b in m.OLD.items(): (self.root/k).write_bytes(b)
    def kill(self,operation,stage):
        code="import runpy,sys; m=runpy.run_path(sys.argv[1]); m[sys.argv[2]](sys.argv[3],sys.argv[4])"
        r=subprocess.run([sys.executable,"-B","-c",code,str(SOURCE),operation,str(self.root),stage],timeout=10)
        self.assertEqual(r.returncode,-signal.SIGKILL)
    def pair(self,expected):
        self.assertEqual({k:(self.root/k).read_bytes() for k in m.NAMES},expected)
    def test_prepared_crash(self):
        self.kill("start","prepared");self.assertFalse(m.gate(self.root))
        self.assertEqual(m.recover(self.root),"rolled back");self.pair(m.OLD)
        self.assertTrue(m.gate(self.root))
    def test_pins_first_crash(self):
        self.kill("start","pins");self.assertFalse(m.gate(self.root))
        self.assertEqual(m.recover(self.root),"rolled back");self.pair(m.OLD)
    def test_both_renames_before_commit_crash(self):
        self.kill("start","updater");self.pair(m.NEW);self.assertFalse(m.gate(self.root))
        self.assertEqual(m.recover(self.root),"rolled back");self.pair(m.OLD)
    def test_committed_crash(self):
        self.kill("start","committed");self.assertTrue(m.gate(self.root))
        self.assertEqual(m.recover(self.root),"committed");self.pair(m.NEW)
    def test_recovery_interrupted(self):
        self.kill("start","updater");self.kill("recover","restore-updater")
        self.assertFalse(m.gate(self.root))
        self.assertEqual(m.recover(self.root),"rolled back");self.pair(m.OLD)
        self.assertEqual(m.recover(self.root),"no transaction")
    def test_unknown_generation_preserved(self):
        self.kill("start","pins")
        (self.root/"updater").write_bytes(b"third party")
        before={k:(self.root/k).read_bytes() for k in m.NAMES}
        with self.assertRaises(RuntimeError):m.recover(self.root)
        self.pair(before);self.assertFalse(m.gate(self.root))
    def test_corrupt_backup_preserved(self):
        self.kill("start","updater")
        (self.root/"pins.backup").write_bytes(b"corrupt")
        with self.assertRaises(RuntimeError):m.recover(self.root)
        self.pair(m.NEW);self.assertFalse(m.gate(self.root))
