"""Native adapter contracts, simulated boot boundaries, no native writes."""
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid
import test_v23_release_gate as prior

DIR=Path(__file__).resolve().parents[2]/"xray/candidates/geo-independent-v23"
with patch.object(sys,"path",[str(DIR),*sys.path]):
    spec=importlib.util.spec_from_file_location("native_gate",DIR/"native_gate.py")
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class NativeContractTests(unittest.TestCase):
    def setUp(self):
        self.boot=str(uuid.uuid4())
        self.base=dict(current_boot=self.boot,accepted_boot=self.boot,receipt_present=False,
                       journal_phase=None,pair="old",lock_exists=True,legacy_fenced=True)
    def decision(self,**changes):
        return m.boot_decision(**dict(self.base,**changes))
    def test_boot_gate(self):
        self.assertEqual(self.decision(),"ALLOW_OLD")
        self.assertEqual(self.decision(current_boot=str(uuid.uuid4())),"BLOCK_BOOT_REACCEPT")
        self.assertEqual(self.decision(current_boot=None,accepted_boot=None),"BLOCK_BOOT_REACCEPT")
        self.assertEqual(self.decision(current_boot="bad",accepted_boot="bad"),"BLOCK_BOOT_REACCEPT")
        self.assertEqual(self.decision(lock_exists=False),"BLOCK_MISSING_LOCK")
        self.assertEqual(self.decision(legacy_fenced=False),"BLOCK_LEGACY")
        self.assertEqual(self.decision(legacy_fenced=1),"BLOCK_LEGACY")
    def test_receipt_survives_boot_fence(self):
        self.assertEqual(self.decision(current_boot=str(uuid.uuid4()),receipt_present=True),"BLOCK_RECEIPT")
        self.assertEqual(self.decision(receipt_present=True,journal_phase="committed",pair="new"),"BLOCK_RECEIPT")
    def test_journal_phases(self):
        for phase in ("prepared","rollback"):
            self.assertEqual(self.decision(journal_phase=phase,pair="unknown"),"RECOVER_UNDER_LOCK")
            self.assertEqual(self.decision(journal_phase=phase,legacy_fenced=False),"BLOCK_LEGACY")
        self.assertEqual(self.decision(journal_phase="committed",pair="new"),"ALLOW_NEW")
        for phase,pair in (("committed","old"),(None,"new"),("corrupt","old"),(None,"unknown")):
            self.assertEqual(self.decision(journal_phase=phase,pair=pair),"BLOCK_GENERATION")
    def test_mount_longest_and_read_only(self):
        text="1 0 0:1 / / rw - tmpfs tmpfs rw\n2 1 8:1 / /media/usb rw - ext4 /dev/sda1 rw\n3 2 0:2 / /media/usb/tmp ro - tmpfs tmpfs ro"
        self.assertEqual(m.mount_record("/media/usb/etc",text)["fs"],"ext4")
        self.assertFalse(m.mount_record("/media/usb/tmp/x",text)["rw"])
        self.assertEqual(m.mount_record("/media/usb2",text)["fs"],"tmpfs")
    def test_mount_escape(self):
        text="1 0 8:1 / /media/my\\040usb rw - ext4 /dev/sda1 rw"
        self.assertEqual(m.mount_record("/media/my usb/etc",text)["device"],"8:1")
    def test_read_no_symlink_or_hardlink(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"file";p.write_bytes(b"fixture");p.chmod(0o600)
            self.assertEqual(m.read_regular(p,True,os.geteuid()),b"fixture")
            q=Path(d)/"link";q.symlink_to(p)
            with self.assertRaises(OSError):m.read_regular(q,True,os.geteuid())
            q.unlink();os.link(p,q)
            with self.assertRaises(m.Blocked):m.read_regular(p,True,os.geteuid())
    def test_rc2_commands_use_exact_pin_pair_and_no_nested_idle(self):
        for pins in (m.OLD_PINS,m.NEW_PINS):
            a,b=m.rc2_commands(pins)
            self.assertEqual(a[:4],[m.PYTHON,"-B","-m","monitoring.full_subscription_snapshot"])
            self.assertEqual(a[5::2],[name+"="+pins[name] for name in m.NAMES])
            self.assertEqual(b,[m.PYTHON,"-B","-m","monitoring.rc2_snapshot","probe","--full",m.FULL,"--publish"])
        with self.assertRaises(m.Blocked):m.rc2_commands(dict(m.NEW_PINS,setup_xray="wrong"))
    def test_rc2_refresh_failure_does_not_probe(self):
        calls=[]
        def run(argv,**kw):calls.append((argv,kw));return 1
        self.assertEqual(m.rc2_runner(m.NEW_PINS,run),1)
        self.assertEqual(len(calls),1)
    def test_rc2_success_calls_both_in_stage(self):
        calls=[]
        def run(argv,**kw):calls.append((argv,kw));return 0
        self.assertEqual(m.rc2_runner(m.OLD_PINS,run),0)
        self.assertEqual(len(calls),2)
        self.assertTrue(all(k=={"cwd":str(m.STAGE)} for _,k in calls))

class BootPersistenceTests(unittest.TestCase):
    # Reuse fixture creation without inheriting/repeating prior tests.
    def setUp(self):
        self.fixture=prior.GateTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.g=self.fixture.g
        self.boot=str(uuid.uuid4());self.next_boot=str(uuid.uuid4())
    def policy(self,accepted,phase,pair,**kw):
        return m.boot_decision(current_boot=self.next_boot,accepted_boot=accepted,
               journal_phase=phase,pair=pair,receipt_present=self.g.receipt.exists(),
               lock_exists=self.g.lock.exists(),legacy_fenced=kw.get("legacy",True))
    def new_lock(self):
        # Simulate volatile lock loss and boot initialization, fixture only.
        old=self.g.lock.with_name("previous-boot.lock")
        self.g.lock.rename(old);self.g.lock.touch(mode=0o600)
        self.assertNotEqual(old.stat().st_ino,self.g.lock.stat().st_ino)
    def test_prepared_persisted_after_simulated_reboot(self):
        self.fixture.killed("install","pins")
        j=self.g.journal.read_bytes();self.new_lock()
        self.assertEqual(self.policy(self.boot,"prepared","unknown"),"BLOCK_BOOT_REACCEPT")
        self.assertEqual(self.g.journal.read_bytes(),j)
        self.assertEqual(self.policy(self.next_boot,"prepared","unknown"),"RECOVER_UNDER_LOCK")
        self.assertEqual(self.g.recover(),"old")
        self.fixture.old()
    def test_committed_pair_persisted_after_simulated_reboot(self):
        self.g.install(self.fixture.candidate);self.new_lock()
        self.assertEqual(self.policy(self.boot,"committed","new"),"BLOCK_BOOT_REACCEPT")
        self.assertEqual(self.policy(self.next_boot,"committed","new"),"ALLOW_NEW")
        self.assertEqual(self.g.recover(),"new")
    def test_old_receipt_blocks_even_after_boot_reaccept(self):
        self.fixture.killed("cron","before-wrapper");self.new_lock()
        self.assertEqual(self.policy(self.next_boot,None,"old"),"BLOCK_RECEIPT")
        with self.assertRaises(prior.m.Blocked):self.g.recover()
