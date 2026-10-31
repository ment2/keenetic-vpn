"""Linux 4.9 parent-owned child safety invariants (disposable local processes)."""
import inspect
import os
from pathlib import Path
import signal
import sys
import tempfile
import unittest
from unittest.mock import patch

from xray.lab import v30_parent_owned_kernel49 as owner
from xray.staging.v30_supervisor_core import FenceError


class ParentOwnedKernel49Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)

    def test_pdeathsig_constant_from_legacy_linux(self):
        self.assertEqual(owner.PR_SET_PDEATHSIG,1)

    def test_start_requires_absolute_executable_and_matching_argv(self):
        for exe,args in (("python",["python"]),("/bin/python",["other"])):
            with self.subTest(exe=exe):
                with self.assertRaises(FenceError):
                    owner.spawn_owned(exe,args,self.root/"prepared.json")

    def test_unreconciled_prepared_journal_denies_new_child(self):
        path=self.root/"prepared.json"
        path.write_text("PREEXISTING_JOURNAL")
        with self.assertRaisesRegex(FenceError,"unreconciled"):
            owner.spawn_owned(sys.executable,[sys.executable,"-c","pass"],path)

    def test_non_parent_cannot_signal_unrelated_pid(self):
        record=owner.Owned(os.getpid(),1,999999,(sys.executable,))
        with self.assertRaisesRegex(FenceError,"another parent's"):
            owner.owned_signal(record,signal.SIGTERM)

    def test_unowned_stale_pid_guard_denies(self):
        record=owner.Owned(os.getpid(),1,os.getpid(),(sys.executable,))
        with self.assertRaises(FenceError):
            owner.owned_signal(record,signal.SIGTERM)

    def test_sole_reaper_owned_child_receives_signal_then_reap(self):
        child=owner.spawn_owned(sys.executable,
            [sys.executable,"-c","import time;time.sleep(30)"],
            self.root/"prepared.json")
        try:
            self.assertEqual(owner.child_owner_status(child),"ALIVE_OWNED")
            self.assertEqual(owner.owned_signal(child,signal.SIGTERM),
                             "SENT_TO_DIRECT_CHILD_WITH_RESERVED_PID")
            owner.reap_owned(child,timeout=5)
            rec=(self.root/"prepared.json").read_text()
            self.assertIn("PREPARED_PARENT_OWNED",rec)
        finally:
            try:os.waitpid(child.pid,os.WNOHANG)
            except ChildProcessError:pass

    def test_preexec_gate_keeps_child_unexecuted_on_journal_fail(self):
        marker=self.root/"marker"
        with patch.object(owner,"atomic_journal",side_effect=FenceError("fsync_denied")):
            with self.assertRaisesRegex(FenceError,"fsync_denied"):
                owner.spawn_owned(sys.executable,
                    [sys.executable,"-c",f"from pathlib import Path;Path({str(marker)!r}).write_text('BAD')"],
                    self.root/"prepared.json")
        self.assertFalse(marker.exists())

    def test_double_spawn_with_same_journal_is_denied(self):
        child=owner.spawn_owned(sys.executable,
            [sys.executable,"-c","import time;time.sleep(30)"],
            self.root/"prepared.json")
        try:
            with self.assertRaises(FenceError):
                owner.spawn_owned(sys.executable,
                    [sys.executable,"-c","import time;time.sleep(30)"],
                    self.root/"prepared.json")
            owner.owned_signal(child,signal.SIGTERM)
            owner.reap_owned(child)
        finally:
            try:os.waitpid(child.pid,os.WNOHANG)
            except ChildProcessError:pass

    def test_no_pidfd_and_no_killall_and_no_orphan_targeting(self):
        src=inspect.getsource(owner)
        self.assertNotIn("pidfd_open(",src)
        self.assertNotIn("pidfd_send_signal(",src)
        self.assertNotIn("killall xray",src)
        self.assertIn("os.kill(child.pid, sig)",src)
        self.assertIn("os.waitid(os.P_PID, child.pid",src)
        self.assertIn("os.WNOWAIT",src)
        self.assertIn("PR_SET_PDEATHSIG",src)

    def test_no_stale_signal_in_mips_recovery(self):
        from xray.lab import v30_parent_owned_mips_recovery as recovery
        source=inspect.getsource(recovery)
        self.assertNotIn("os.kill(",source)
        self.assertNotIn("pidfd_open(",source)
        self.assertIn("while alive(previous[",source)
        self.assertIn("owned_signal(child,signal.SIGTERM)",source)


if __name__=="__main__":
    unittest.main()
