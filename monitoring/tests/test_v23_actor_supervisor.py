"""Real process tests and integrated actor admission on disposable fixtures."""
import importlib.util
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
import unittest
from dataclasses import replace
from unittest.mock import patch
import test_v23_lock_migration as migration

DIR=Path(__file__).resolve().parents[2]/"xray/candidates/geo-independent-v23"
with patch.object(sys,"path",[str(DIR),*sys.path]):
    sys.modules["lock_migration"]=migration.m
    spec=importlib.util.spec_from_file_location("actor_supervisor",DIR/"actor_supervisor.py")
    m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)

class ProcessTests(unittest.TestCase):
    def spawn(self):
        p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(60)"])
        def cleanup():
            if p.poll() is None:p.terminate()
            p.wait(timeout=5)
        self.addCleanup(cleanup)
        return p
    def test_exact_identity_and_wrong_start_ticks(self):
        p=self.spawn()
        i=m.identity(p.pid)
        self.assertEqual(i.ppid,os.getpid())
        self.assertEqual(i.argv[0],os.fsencode(sys.executable))
        if not hasattr(os,"pidfd_open"):self.skipTest("pidfd absent")
        with self.assertRaises(m.Blocked):m.Handle(replace(i,start=i.start+1))
        self.assertIsNone(p.poll())
    def test_pidfd_targets_only_owned_identity(self):
        if not hasattr(os,"pidfd_open"):self.skipTest("pidfd absent")
        p=self.spawn();other=self.spawn()
        with m.Handle(m.identity(p.pid)) as handle:handle.terminate()
        self.assertEqual(p.wait(timeout=5),-signal.SIGTERM)
        self.assertIsNone(other.poll())
    def test_wrong_boot_identity_blocks(self):
        if not hasattr(os,"pidfd_open"):self.skipTest("pidfd absent")
        p=self.spawn()
        with self.assertRaises(m.Blocked):m.Handle(replace(m.identity(p.pid),boot="wrong"))
        self.assertIsNone(p.poll())
    def test_no_pidfd_no_signal_fallback(self):
        p=self.spawn()
        with patch.object(os,"pidfd_open",side_effect=OSError(38,"not implemented")),patch.object(os,"kill") as kill:
            with self.assertRaises(OSError):m.Handle(m.identity(p.pid))
            kill.assert_not_called()
        self.assertIsNone(p.poll())
    def test_wrong_config_cannot_adopt_probe_as_main(self):
        p=self.spawn()
        with self.assertRaises(m.Blocked):m.match_main(p.pid,sys.executable,"/fixture/config.json")
        self.assertIsNone(p.poll())
    def test_real_listener_owner_and_nonowner(self):
        p=self.spawn()
        with socket.socket() as sock:
            sock.bind(("127.0.0.1",0));sock.listen()
            port=sock.getsockname()[1]
            self.assertTrue(m.listener_owned(os.getpid(),port))
            self.assertFalse(m.listener_owned(p.pid,port))
    def test_direct_child_supervisor_keeps_other_process(self):
        p=self.spawn()
        child=m.OwnedChild([sys.executable,"-c","import time;time.sleep(60)"])
        try:
            child.stop()
            self.assertTrue(child.reaped)
            self.assertIsNone(p.poll())
            with self.assertRaises(m.Blocked):child.stop()
        finally:
            if not child.reaped:child.stop()
    def test_direct_child_requires_exclusive_reaper(self):
        old=signal.signal(signal.SIGCHLD,signal.SIG_IGN)
        try:
            with self.assertRaises(m.Blocked):m.OwnedChild([sys.executable,"-c","pass"])
        finally:signal.signal(signal.SIGCHLD,old)
    def test_exited_unreaped_child_does_not_target_other_process(self):
        p=self.spawn()
        child=m.OwnedChild([sys.executable,"-c","pass"])
        time.sleep(.15)
        child.stop()
        self.assertTrue(child.reaped)
        self.assertIsNone(p.poll())

class ActorTests(unittest.TestCase):
    def setUp(self):
        self.fixture=migration.IntegratedMigrationTests()
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.g=self.fixture.g;self.r=self.fixture.r
        self.calls=[]
        self.health=False;self.rules=False
        def restart():
            self.calls.append("restart");self.health=True
            with self.assertRaises(BlockingIOError):self.g.release(self.r,"cron")
            return 0
        def repair():
            self.calls.append("repair");self.rules=True
            with self.assertRaises(BlockingIOError):self.g.run("S97",lambda _:0,gate=self.r)
            return 0
        self.a=m.Actors(self.g,self.r,restart=restart,healthy=lambda:self.health,
                        rules_ok=lambda:self.rules,repair=repair,
                        monitor=lambda pins:0 if pins==self.r.old else 1)
    def test_watchdog_delegates_once_without_nested_flock(self):
        self.assertEqual(self.a.watchdog(),"protected")
        self.assertEqual(self.a.watchdog(),"protected")
        self.assertEqual(self.calls,["restart"])
    def test_s97_s98_cron_and_rc2_share_gate(self):
        self.assertEqual(self.a.s97(),"protected")
        self.assertEqual(self.a.s98(),"protected")
        self.assertEqual(self.a.s98(),"protected")
        self.assertEqual(self.a.cron(),"old")
        self.assertEqual(self.a.rc2(),"old")
        self.assertEqual(self.calls,["restart","repair"])
    def test_actor_receipt_blocks_even_with_environment_marker(self):
        self.g.receipt.write_text("fixture ambiguity")
        with patch.dict(os.environ,{"XRAY_GATE_HELD":"1","XRAY_OWNER_PID":str(os.getpid())}):
            for fn in (self.a.s97,self.a.watchdog,self.a.s98,self.a.cron,self.a.rc2):
                with self.assertRaises(m.Blocked):fn()
        self.assertEqual(self.calls,[])
    def test_changed_descriptor_blocks_all_actors(self):
        (self.g.actors/"S97").write_text("ungated")
        for fn in (self.a.s97,self.a.watchdog,self.a.s98,self.a.cron,self.a.rc2):
            with self.assertRaises(m.Blocked):fn()
        self.assertEqual(self.calls,[])
    def test_failed_rule_repair_fences_following_cron(self):
        self.a.repair=lambda:1
        with self.assertRaises(m.Blocked):self.a.s98()
        with self.assertRaises(m.Blocked):self.a.cron()
        self.assertTrue(self.g.receipt.exists())

class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.fixture=migration.IntegratedMigrationTests()
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.g=self.fixture.g
        self.argv=[sys.executable,"-c","import time;time.sleep(60)"]
    def test_receipt_persists_while_service_runs_and_no_adoption(self):
        service=m.Lifecycle(self.g,self.argv,lambda pid:True)
        try:
            self.assertEqual(service.start(),0)
            self.assertTrue(service.healthy())
            self.assertTrue(service.path.exists())
            successor=m.Lifecycle(self.g,self.argv,lambda pid:True)
            with self.assertRaises(m.Blocked):successor.start()
            self.assertEqual(service.restart(),0)
            self.assertTrue(service.healthy())
        finally:
            if service.child is not None and not service.child.reaped:service.stop()
        self.assertFalse(service.path.exists())
    def test_failed_start_retains_receipt(self):
        service=m.Lifecycle(self.g,self.argv,lambda pid:False)
        with self.assertRaises(m.Blocked):service.start(timeout=.2)
        self.assertTrue(service.child.reaped)
        self.assertTrue(service.path.exists())
        with self.assertRaises(m.Blocked):m.Lifecycle(self.g,self.argv,lambda pid:True).start()
    def test_external_reap_detected_before_signal(self):
        child=m.OwnedChild([sys.executable,"-c","pass"])
        os.waitpid(child.pid,0)
        with patch.object(os,"kill") as kill:
            with self.assertRaises(ChildProcessError):child.stop()
            kill.assert_not_called()
