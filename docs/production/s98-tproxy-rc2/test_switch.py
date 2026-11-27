import importlib.util, tempfile, unittest, os, hashlib, json
from pathlib import Path
from unittest.mock import patch
p=Path(__file__).with_name('s98-switch.py'); spec=importlib.util.spec_from_file_location('switch',p); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
def legacy(pid=23941,ticks='8326634',state='S'): return (pid,ticks,state,1,[b'/opt/bin/sh',os.fsencode(m.TARGET),b'start'])
class Tests(unittest.TestCase):
 def test_exact_identity(self): self.assertEqual(m.role(legacy()),'legacy'); self.assertNotEqual(m.identity(legacy()),m.identity(legacy(ticks='2'))); self.assertIsNone(m.role((703,'1','S',1,[b'cron'])))
 def test_legacy_reused_pid_no_signal(self):
  with patch.object(m,'scan',return_value=[legacy(ticks='2')]),patch.object(m,'boot',return_value='boot'),patch.object(m.os,'kill') as k:
   with self.assertRaises(m.Block): m.legacy_stop(legacy(),'boot')
   k.assert_not_called()
 def test_legacy_busy_child_no_signal(self):
  a=legacy(); child=(999,'2','S',a[0],[b'/bin/sh',b'/opt/bin/xray-wifi-rules.sh'])
  with patch.object(m,'scan',return_value=[a,child]),patch.object(m,'boot',return_value='boot'),patch.object(m.os,'kill') as k:
   with self.assertRaises(m.Block): m.legacy_stop(a,'boot')
   k.assert_not_called()
 def test_legacy_boot_drift_no_signal(self):
  with patch.object(m,'scan',return_value=[legacy()]),patch.object(m,'boot',return_value='new'),patch.object(m.os,'kill') as k:
   with self.assertRaises(m.Block): m.legacy_stop(legacy(),'old')
   k.assert_not_called()
 def test_atomic_preserves_mode(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'script'; m.atomic(p,b'old',0o755); m.atomic(p,b'new',0o755); self.assertEqual(p.read_bytes(),b'new'); self.assertEqual(p.stat().st_mode&0o777,0o755)
 def test_backup_exclusive(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'backup'; m.exclusive(p,b'old'); self.assertEqual(p.stat().st_mode&0o777,0o600)
   with self.assertRaises(FileExistsError): m.exclusive(p,b'new')
   self.assertEqual(p.read_bytes(),b'old')
 def test_hash_and_symlink(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'orig'; p.write_bytes(b'old'); h=hashlib.sha256(b'old').hexdigest(); self.assertEqual(m.read(p,h),b'old'); l=Path(d)/'link'; l.symlink_to(p)
   with self.assertRaises(m.Block): m.read(l,h)
   with self.assertRaises(m.Block): m.read(p,'bad')
 def test_stale_cleanup_refuses_live_watcher(self):
  with patch.object(m,'scan',return_value=[legacy()]):
   with self.assertRaises(m.Block): m.clear_stale()
 def test_phase_refuses_boot_drift(self):
  with tempfile.TemporaryDirectory() as d:
   with patch.object(m,'D',Path(d)),patch.object(m,'boot',return_value='old'): m.state('PREPARED')
   with patch.object(m,'D',Path(d)),patch.object(m,'boot',return_value='new'):
    with self.assertRaises(m.Block): m.phase()
 def test_start_requires_phase(self):
  with patch.object(m,'phase',return_value='START_INTENT'),patch.object(m,'quiet') as q:
   with self.assertRaises(m.Block): m.start()
   q.assert_not_called()
 def test_rollback_restore_refuses_rc2(self):
  a=(999,'1','S',1,[os.fsencode(m.PY),os.fsencode(m.TARGET),b'watch',b'7',b'9'])
  with patch.object(m,'phase',return_value='ROLLBACK_STOPPED'),patch.object(m,'read'),patch.object(m,'check'),patch.object(m,'gate'),patch.object(m,'digest',return_value=m.NEW),patch.object(m,'scan',return_value=[a]),patch.object(m,'atomic') as w:
   with self.assertRaises(m.Block): m.rollback_restore()
   w.assert_not_called()
 def test_rollback_restores_only_known_hash(self):
  with patch.object(m,'phase',return_value='ROLLBACK_STOPPED'),patch.object(m,'read'),patch.object(m,'check'),patch.object(m,'gate'),patch.object(m,'digest',return_value='foreign'),patch.object(m,'atomic') as w:
   with self.assertRaises(m.Block): m.rollback_restore()
   w.assert_not_called()
if __name__=='__main__': unittest.main(verbosity=2)
