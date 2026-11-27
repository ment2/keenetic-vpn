"""New migration tests; old acceptance evidence is not re-run as a live trial."""
import fcntl
import importlib.util
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid

DIR=Path(__file__).resolve().parents[2]/"xray/candidates/geo-independent-v23"
with patch.object(sys,"path",[str(DIR),*sys.path]):
    spec=importlib.util.spec_from_file_location("lock_migration",DIR/"lock_migration.py")
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="v23-lock-fixture-")
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/"marker").write_bytes(b"synthetic-only")
        self.boot=str(uuid.uuid4())
        self.g=m.Migration(self.root,self.boot)
        for p in (self.g.old.parent,self.g.protected,self.g.actors):
            p.mkdir(parents=True,mode=0o700)
        self.g.old.parent.chmod(0o777)
        for p in (self.g.old,self.g.control):p.touch(mode=0o600);p.chmod(0o600)
        for a in m.ACTORS:
            p=self.g.actors/a;p.write_text("gated-fixture:"+a);p.chmod(0o600)
        self.ident=self.g.identity(self.g.old)
        self.g.initialize(True)

    def killed(self,op,stage):
        code="""import runpy,sys,os,signal
d=runpy.run_path(sys.argv[1])
def cut(s):
 if s==sys.argv[4]:os.kill(os.getpid(),signal.SIGKILL)
g=d['m'].Migration(sys.argv[2],sys.argv[3],cut=cut)
op=sys.argv[5]
if op=='actor':g.run('cron',lambda _:0)
else:getattr(g,op)()
"""
        r=subprocess.run([sys.executable,"-B","-c",code,__file__,str(self.root),self.boot,stage,op],timeout=10)
        self.assertEqual(r.returncode,-signal.SIGKILL)

    def assert_path(self,path,phase):
        self.assertEqual(self.g.state()["phase"],phase)
        self.assertEqual(self.g.identity(path),self.ident)
        self.assertFalse((self.g.new if path==self.g.old else self.g.old).exists())

    def test_move_preserves_inode_and_all_eight_actors(self):
        self.g.migrate();self.assert_path(self.g.new,"protected")
        seen=[]
        for a in m.ACTORS:
            self.assertEqual(self.g.run(a,lambda p:(seen.append(self.g.identity(p)),0)[1]),"protected")
        self.assertEqual(seen,[self.ident]*8)
        self.g.rollback();self.assert_path(self.g.old,"legacy")

    def test_old_external_flock_blocks_migration(self):
        with self.g.old.open("rb") as f:
            fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):self.g.migrate()
        self.assert_path(self.g.old,"legacy")
        self.g.migrate()

    def test_preopened_old_fd_contends_with_new_path(self):
        with self.g.old.open("rb") as fd:
            self.g.migrate()
            self.assertEqual([os.fstat(fd.fileno()).st_dev,os.fstat(fd.fileno()).st_ino],self.ident)
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            r=subprocess.run(["flock","-n",str(self.g.new),"/bin/true"],timeout=5)
            self.assertNotEqual(r.returncode,0)
            with self.assertRaises(BlockingIOError):self.g.run("cron",lambda _:0)
        self.assertEqual(self.g.run("cron",lambda _:0),"protected")

    def test_cross_actor_exclusion_under_real_lock(self):
        self.g.migrate()
        def body(p):
            for a in m.ACTORS:
                with self.assertRaises(BlockingIOError):self.g.run(a,lambda _:0)
            r=subprocess.run(["flock","-n",str(p),"/bin/true"],timeout=5)
            self.assertNotEqual(r.returncode,0)
            with self.assertRaises(BlockingIOError):self.g.rollback()
            return 0
        self.g.run("watchdog",body)

    def test_crash_before_rename(self):
        self.killed("migrate","prepared");self.assert_path(self.g.old,"prepared")
        with self.assertRaises(m.Blocked):self.g.run("RC2-probe",lambda _:0)
        self.assertEqual(self.g.recover(),"legacy")

    def test_crash_after_rename_before_commit(self):
        self.killed("migrate","renamed");self.assert_path(self.g.new,"prepared")
        with self.assertRaises(m.Blocked):self.g.run("cron",lambda _:0)
        self.assertEqual(self.g.recover(),"legacy");self.assert_path(self.g.old,"legacy")

    def test_crash_after_commit(self):
        self.killed("migrate","protected")
        self.assertEqual(self.g.recover(),"protected");self.assert_path(self.g.new,"protected")

    def test_rollback_crash_before_move(self):
        self.g.migrate();self.killed("rollback","rollback")
        self.assertEqual(self.g.recover(),"legacy");self.assert_path(self.g.old,"legacy")

    def test_rollback_crash_after_move(self):
        self.g.migrate();self.killed("rollback","renamed")
        self.assertEqual(self.g.recover(),"legacy");self.assert_path(self.g.old,"legacy")

    def test_reboot_requires_fresh_acceptance(self):
        self.g.migrate()
        other=m.Migration(self.root,str(uuid.uuid4()))
        with self.assertRaises(m.Blocked):other.run("S98",lambda _:0)
        with self.assertRaises(m.Blocked):other.recover(reaccept=True,drained=False)
        self.assertEqual(other.recover(reaccept=True,drained=True),"protected")
        self.assertEqual(other.run("S98",lambda _:0),"protected")

    def test_receipt_fences_reboot_even_after_reaccept(self):
        self.g.migrate();self.killed("actor","before-actor")
        other=m.Migration(self.root,str(uuid.uuid4()))
        with self.assertRaises(m.Blocked):other.recover(reaccept=True,drained=True)
        with self.assertRaises(m.Blocked):other.run("cron",lambda _:0)
        self.assertTrue(other.receipt.exists())

    def test_missing_lock_never_recreated(self):
        self.g.migrate();self.g.new.unlink()
        with self.assertRaises(m.Blocked):self.g.recover()
        self.assertFalse(self.g.new.exists());self.assertFalse(self.g.old.exists())

    def test_legacy_recreates_path_blocks_cooperating_gate(self):
        self.g.migrate()
        # Explicit residual risk witness: unmodified actors can still create
        # and acquire a DIFFERENT inode at the abandoned world-writable path.
        self.g.old.touch(mode=0o600)
        self.assertNotEqual(self.g.identity(self.g.old),self.ident)
        r=subprocess.run(["flock","-n",str(self.g.old),"/bin/true"],timeout=5)
        self.assertEqual(r.returncode,0)
        with self.assertRaises(m.Blocked):self.g.run("cron",lambda _:0)
        with self.assertRaises(m.Blocked):self.g.recover()
        self.assertTrue(self.g.old.exists());self.assertTrue(self.g.new.exists())

    def test_uncooperative_actor_can_bypass_old_path_mid_run(self):
        self.g.migrate()
        def body(p):
            self.g.old.touch(mode=0o600)
            r=subprocess.run(["flock","-n",str(self.g.old),"/bin/true"],timeout=5)
            self.assertEqual(r.returncode,0)
            return 0
        # The next readback blocks and retains receipt, but a raw legacy
        # action already ran. This is a negative safety witness, not a pass
        # for arbitrary privileged actor fencing.
        with self.assertRaises(m.Blocked):self.g.run("cron",body)
        self.assertTrue(self.g.receipt.exists())
        with self.assertRaises(m.Blocked):self.g.recover()

    def test_foreign_actor_or_ungated_script_blocks(self):
        p=self.g.actors/"watchdog";p.write_text("legacy")
        with self.assertRaises(m.Blocked):self.g.migrate()
        p.write_text("gated-fixture:watchdog")
        (self.g.actors/"unexpected").touch()
        with self.assertRaises(m.Blocked):self.g.run("S97",lambda _:0)
        self.assert_path(self.g.old,"legacy")

    def test_noreplace_does_not_overwrite_destination(self):
        self.g.new.write_bytes(b"foreign")
        with self.assertRaises(FileExistsError):m.rename_noreplace(self.g.old,self.g.new)
        self.assertEqual(self.g.new.read_bytes(),b"foreign")
        self.assertEqual(self.g.identity(self.g.old),self.ident)

    def test_nonzero_actor_keeps_receipt(self):
        self.g.migrate()
        with self.assertRaises(m.Blocked):self.g.run("legacy-openai",lambda _:1)
        with self.assertRaises(m.Blocked):self.g.rollback()

    def test_control_directory_symlink_rejected(self):
        moved=self.g.protected.with_name("other")
        self.g.protected.rename(moved);self.g.protected.symlink_to(moved)
        with self.assertRaises(m.Blocked):self.g.run("cron",lambda _:0)


class IntegratedMigrationTests(unittest.TestCase):
    def setUp(self):
        import test_v23_release_gate as prior
        self.prior=prior
        self.fixture=prior.GateTests()
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.r=self.fixture.g
        self.g=m.Migration(self.fixture.root,str(uuid.uuid4()))
        for p in (self.g.protected,self.g.actors):p.mkdir(mode=0o700)
        self.g.control.touch(mode=0o600)
        for a in m.ACTORS:
            p=self.g.actors/a;p.write_text("gated-fixture:"+a);p.chmod(0o600)
        self.g.initialize(True);self.g.migrate()

    def test_release_and_actor_share_one_inode_until_source_rollback(self):
        self.g.release(self.r,"install",candidate=self.fixture.candidate)
        self.assertEqual(self.g.release(self.r,"cron"),"new")
        self.assertEqual(self.g.release(self.r,"monitor",runner=lambda pins:0 if pins==self.r.new else 1),"new")
        for a in ("watchdog","S97","S98","legacy-vless","legacy-openai"):
            self.assertEqual(self.g.run(a,lambda p:0,gate=self.r),"protected")
        with self.assertRaises(m.Blocked):self.g.rollback()
        self.assertEqual(self.g.release(self.r,"rollback"),"old")
        self.g.rollback()
        self.assertTrue(self.g.old.exists())
        self.assertTrue(self.r.pair_matches(self.r.old))

    def test_release_receipt_fences_all_migration_actors(self):
        bad=b"#!/bin/sh\nexit 1\n";self.r.wrapper.write_bytes(bad);self.r.wrapper_sha=self.prior.m.sha(bad)
        with self.assertRaises(self.prior.m.Blocked):self.g.release(self.r,"cron")
        self.assertTrue(self.r.receipt.exists())
        with self.assertRaises(m.Blocked):self.g.run("S98",lambda _:0,gate=self.r)
        with self.assertRaises(m.Blocked):self.g.rollback()
        with self.assertRaises(m.Blocked):self.g.recover()

    def test_actor_receipt_fences_release(self):
        with self.assertRaises(m.Blocked):self.g.run("watchdog",lambda _:1,gate=self.r)
        with self.assertRaises(m.Blocked):self.g.release(self.r,"cron")
        self.assertFalse(self.fixture.trace.exists())

    def test_prepared_release_pair_blocks_other_actors_until_recovery(self):
        def cut(stage):
            if stage=="pins":raise RuntimeError("synthetic interruption")
        self.r.cut=cut
        with self.assertRaises(RuntimeError):self.g.release(self.r,"install",candidate=self.fixture.candidate)
        with self.assertRaises(self.prior.m.Blocked):self.g.run("S97",lambda _:0,gate=self.r)
        self.r.cut=lambda _:None
        self.assertEqual(self.g.release(self.r,"recover"),"old")
        self.assertEqual(self.g.run("S97",lambda _:0,gate=self.r),"protected")

    def test_release_gate_checks_expected_inode_before_child(self):
        self.r.lock=self.g.new
        self.r.expected_lock_id=(0,0)
        with self.assertRaises(self.prior.m.Blocked):self.r.cron()
        self.assertFalse(self.fixture.trace.exists())
        self.assertFalse(self.r.receipt.exists())
