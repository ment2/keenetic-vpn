"""Exercise the release gate in disposable directories, including real SIGKILL."""
import importlib.util
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

SOURCE=Path(__file__).resolve().parents[2]/"xray/candidates/geo-independent-v23/release_gate.py"
spec=importlib.util.spec_from_file_location("gate",SOURCE)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

OLD=b"# old fixture\n"
NEW=b"# new fixture\n"
WRAPPER=b'#!/bin/sh\nset -eu\nprintf "%s\\n" ran >> "$(dirname "$0")/trace"\n'
def plan():
    return dict(zip(m.NAMES,[m.sha(OLD)]+[m.sha(n.encode()) for n in m.NAMES[1:]]))

def gate(root,cut=lambda _:None):
    return m.Gate(root,plan(),m.sha(NEW),m.sha(WRAPPER),cut=cut)

class GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="v23-release-fixture-")
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/"marker").write_bytes(b"synthetic-only")
        self.g=gate(self.root)
        for p in (self.g.bin,self.g.pins.parent,self.g.lock.parent,self.g.state):
            p.mkdir(parents=True,mode=0o700)
        for p,b,mode in [(self.g.up,OLD,0o755),(self.g.pins,m.encode(plan()),0o600),
                         (self.g.lock,b"",0o600),(self.g.wrapper,WRAPPER,0o755),
                         (self.root/"candidate",NEW,0o600)]+[(self.g.bin/n,n.encode(),0o755) for n in m.NAMES[1:]]:
            p.write_bytes(b);p.chmod(mode)
        self.candidate=self.root/"candidate"
        self.trace=self.g.bin/"trace"

    def child(self,operation,stage):
        code="""import runpy,sys,os,signal
d=runpy.run_path(sys.argv[1])
def cut(s):
 if s==sys.argv[4]:os.kill(os.getpid(),signal.SIGKILL)
g=d['gate'](sys.argv[2],cut)
op=sys.argv[3]
if op=='install':g.install(g.root/'candidate')
elif op=='rollback':g.recover(True)
else:getattr(g,op)()
"""
        return subprocess.run([sys.executable,"-B","-c",code,__file__,str(self.root),operation,stage],timeout=10)
    def killed(self,op,stage):
        self.assertEqual(self.child(op,stage).returncode,-signal.SIGKILL)
    def old(self):
        self.assertTrue(self.g.pair_matches(self.g.old))
        self.assertEqual(self.g.up.stat().st_mode&0o777,0o755)
        self.assertEqual(self.g.pins.stat().st_mode&0o777,0o600)
    def test_install_commit_cron_and_rollback(self):
        self.assertEqual(self.g.cron(),"old")
        self.g.install(self.candidate)
        self.assertEqual(self.g.cron(),"new")
        self.assertEqual(self.g.recover(True),"old")
        self.old()
        self.assertEqual(self.g.cron(),"old")
        self.assertEqual(self.trace.read_text().splitlines(),["ran"]*3)
    def test_cron_recovers_prepared(self):
        self.killed("install","prepared")
        self.assertEqual(self.g.cron(),"old");self.old()
    def test_cron_recovers_mixed_pair(self):
        self.killed("install","pins")
        self.assertFalse(self.g.pair_matches(self.g.old))
        self.assertEqual(self.g.cron(),"old");self.old()
    def test_cron_recovers_uncommitted_new_pair(self):
        self.killed("install","updater")
        self.assertTrue(self.g.pair_matches(self.g.new))
        self.assertEqual(self.g.cron(),"old");self.old()
    def test_cron_keeps_committed_pair(self):
        self.killed("install","committed")
        self.assertEqual(self.g.cron(),"new")
    def test_rollback_recovery_after_kill(self):
        self.g.install(self.candidate)
        self.killed("rollback","restore-updater")
        self.assertEqual(self.g.cron(),"old");self.old()
    def test_receipt_blocks_cron_after_parent_death(self):
        self.killed("cron","before-wrapper")
        self.assertTrue(self.g.receipt.is_file())
        for op in (self.g.cron,self.g.recover,lambda:self.g.install(self.candidate)):
            with self.assertRaises(m.Blocked):op()
        self.assertFalse(self.trace.exists())
    def test_receipt_blocks_after_wrapper_completion_before_clear(self):
        self.killed("cron","after-wrapper")
        with self.assertRaises(m.Blocked):self.g.cron()
        self.assertEqual(self.trace.read_text().splitlines(),["ran"])
    def test_external_lock_contention(self):
        with self.g.held():
            r=subprocess.run(["flock","-n","-o",str(self.g.lock),"/bin/true"],timeout=5)
            self.assertNotEqual(r.returncode,0)
            with self.assertRaises(BlockingIOError):self.g.cron()
        self.assertEqual(self.g.cron(),"old")
    def test_unknown_pair_rejected_without_writes(self):
        self.killed("install","pins")
        self.g.up.write_bytes(b"# foreign")
        before=self.g.pair()
        with self.assertRaises(m.Blocked):self.g.cron()
        self.assertEqual(self.g.pair(),before)
        self.assertFalse(self.trace.exists())
    def test_corrupt_backup_rejected_before_restore(self):
        self.killed("install","updater")
        self.g.backup_pins.write_bytes(b"corrupt")
        before=self.g.pair()
        with self.assertRaises(m.Blocked):self.g.cron()
        self.assertEqual(self.g.pair(),before)
    def test_dependency_or_wrapper_change_blocks(self):
        (self.g.bin/m.NAMES[1]).write_bytes(b"unexpected")
        with self.assertRaises(m.Blocked):self.g.cron()
        self.assertFalse(self.trace.exists())
    def test_wrapper_nonzero_retains_receipt(self):
        bad=b"#!/bin/sh\nexit 1\n";self.g.wrapper.write_bytes(bad)
        self.g.wrapper_sha=m.sha(bad)
        with self.assertRaises(m.Blocked):self.g.cron()
        self.assertTrue(self.g.receipt.is_file())
        with self.assertRaises(m.Blocked):self.g.cron()
    def test_candidate_bad_hash_and_symlink(self):
        self.candidate.write_bytes(b"# wrong")
        with self.assertRaises(m.Blocked):self.g.install(self.candidate)
        self.old()
        self.candidate.unlink();self.candidate.symlink_to(self.g.up)
        with self.assertRaises(OSError):self.g.install(self.candidate)
        self.assertFalse(self.g.journal.exists())
    def test_duplicate_pin_keys_rejected(self):
        p=m.encode(plan()).decode().strip()
        self.g.pins.write_text(p[:-1]+',"xray-update-v23.py":"bad"}')
        with self.assertRaises(m.Blocked):self.g.cron()
    def test_lock_inode_replaced_detected(self):
        with self.g.held():
            self.g.lock.rename(self.g.lock.with_name("old.lock"))
            self.g.lock.write_bytes(b"");self.g.lock.chmod(0o600)
            with self.assertRaises(m.Blocked):self.g.check_lock()
