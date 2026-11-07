"""RC43: actual archived SHA + fresh read-only preflight logic."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from xray.staging import v30_maintenance_preflight_readonly as p
ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/"xray/staging/v30_first_cutover_canary.py"
BOOT="11111111-1111-1111-1111-111111111111"
class Fake:
 ACTIVE=Path("/config")
 STATE=Path("/state")
 READY=Path("/ready")
 def owned_xray_pids(self):return [3001]
 def ticks(self,pid):return 50011
 def checksum(self,path):return "e"*64
 def preflight(self,pid,ticks,sha):
  assert (pid,ticks,sha)==(3001,50011,"e"*64)
  return (2111,100),(2222,101)
class TestRC43(unittest.TestCase):
 def test_existing_canary_bytes_pinned(self):
  raw=ARCHIVE.read_bytes()
  self.assertEqual(hashlib.sha256(raw).hexdigest(),p.CANARY_SHA256)
  blob=hashlib.sha1(b"blob "+str(len(raw)).encode()+bytes([0])+raw).hexdigest()
  self.assertEqual(blob,p.CANARY_GIT_BLOB)
 def test_old_owner_fresh_readonly_can_be_verified_but_not_approved(self):
  with tempfile.TemporaryDirectory() as td:
   boot=Path(td)/"boot";boot.write_text(BOOT)
   with patch.object(p.Path,"exists",return_value=False):
    r=p.inspect(Fake(),getuid=lambda:0,boot_path=boot)
   self.assertEqual(r["old_pid"],3001)
   self.assertEqual(r["old_start_ticks"],50011)
   self.assertEqual(r["first_migration"],"MAINTENANCE_OUTAGE_SESSION_RESET_ALLOWED")
   self.assertFalse(r["legacy_private_activeconn_snapshot_required"])
   self.assertFalse(r["cutover_authorized"])
   self.assertFalse(r["production_modified"])
   self.assertNotIn("credential",json.dumps(r))
 def test_rootless_or_multiple_old_processes_block(self):
  with self.assertRaisesRegex(p.Blocked,"ROOT"):p.inspect(Fake(),getuid=lambda:65534)
  f=Fake();f.owned_xray_pids=lambda:[1,2]
  with self.assertRaisesRegex(p.Blocked,"EXCLUSIVE"):p.inspect(f,getuid=lambda:0)
 def test_wrong_canary_or_symlink_denied_before_import(self):
  with tempfile.TemporaryDirectory() as td:
   f=Path(td)/"canary.py";f.write_text("print('not executed')\n")
   with self.assertRaisesRegex(p.Blocked,"SHA"):p.import_verified(f)
   f.unlink();f.symlink_to(ARCHIVE)
   with self.assertRaisesRegex(p.Blocked,"SYMLINK"):p.import_verified(f)
 def test_live_canary_journal_prevents_next_trial(self):
  with tempfile.TemporaryDirectory() as td:
   boot=Path(td)/"boot";boot.write_text(BOOT)
   f=Fake();f.STATE=Path(td)/"state";f.STATE.touch()
   with self.assertRaisesRegex(p.Blocked,"JOURNAL"):
    p.inspect(f,getuid=lambda:0,boot_path=boot)
 def test_no_signals_or_kernel_writes_in_helper(self):
  src=(ROOT/"xray/staging/v30_maintenance_preflight_readonly.py").read_text()
  for bad in ("os.kill(", "SIGTERM", "SIGSTOP", "subprocess.Popen(", "candidate_config(", "trial(", "rollback(", "guardian(", "write_text(", "mkdir(", "unlink("):
   self.assertNotIn(bad,src)
  self.assertIn("module.preflight(pid,ticks,sha)",src)
 def test_require_independent_backup_and_descendant_fence(self):
  self.assertIn("CURRENT_OFFSITE_ENCRYPTED_BACKUP_AND_RESTORE_TEST",p.PENDING)
  self.assertIn("WATCHDOG_AND_S97_S98_S99_CRON_DESCENDANTS_QUIESCED",p.PENDING)
if __name__=="__main__":unittest.main()
