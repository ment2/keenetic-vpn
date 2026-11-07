"""RC42 tempfile fsync CAS negative mutation checks; not hardware durability."""
from pathlib import Path
from tempfile import TemporaryDirectory
from concurrent.futures import ThreadPoolExecutor
import unittest,json
from xray.lab.rc42_fsync_generation_cas import begin,read,advance,CASBlocked
BOOT="00000000-1111-2222-3333-444444444444"
A="a"*64;B="b"*64
def nxt(r,g=1,boot=BOOT,sha=A,inject=False):
 return advance(r,expected=g,old_phase="ORIGINAL" if g==1 else "FROZEN_DROP",
                new_phase="FROZEN_DROP" if g==1 else "RESTORED",
                boot=boot,old_sha=sha,new_sha=B if g==1 else A,
                pid=1001,ticks="12020",inject=inject)
class Cas(unittest.TestCase):
 def test_actual_fsync_and_exact_rollback_digest(self):
  with TemporaryDirectory() as td:
   r=Path(td)/"receipt";begin(r,BOOT,A,1001,"12020")
   self.assertEqual(read(r)["generation"],1)
   self.assertEqual(nxt(r)["generation"],2)
   self.assertEqual(nxt(r,g=2,sha=B)["generation"],3)
   self.assertEqual(read(r)["rules_sha"],A)
 def test_stale_generation_rejected(self):
  with TemporaryDirectory() as td:
   r=Path(td)/"receipt";begin(r,BOOT,A,1001,"12020");nxt(r)
   with self.assertRaisesRegex(CASBlocked,"STALE"):nxt(r)
   self.assertEqual(read(r)["generation"],2)
 def test_foreign_boot_rejected(self):
  with TemporaryDirectory() as td:
   r=Path(td)/"receipt";begin(r,BOOT,A,1001,"12020")
   with self.assertRaisesRegex(CASBlocked,"STALE"):nxt(r,boot="foreign")
 def test_pid_ticks_rules_mutants(self):
  with TemporaryDirectory() as td:
   r=Path(td)/"receipt";begin(r,BOOT,A,1001,"12020")
   for pid,ticks,sha in [(1002,"12020",A),(1001,"12021",A),(1001,"12020",B)]:
    with self.subTest(pid=pid,ticks=ticks,sha=sha),self.assertRaisesRegex(CASBlocked,"STALE"):
     advance(r,1,"ORIGINAL","FROZEN_DROP",BOOT,sha,B,pid,ticks)
 def test_crash_before_replace_does_not_claim_commit(self):
  with TemporaryDirectory() as td:
   r=Path(td)/"receipt";begin(r,BOOT,A,1001,"12020")
   with self.assertRaisesRegex(CASBlocked,"INJECTED"):nxt(r,inject=True)
   self.assertEqual(read(r)["generation"],1)
   self.assertEqual(list(r.glob(".staged-*")),[])
 def test_corrupted_receipt_sha_denied(self):
  with TemporaryDirectory() as td:
   r=Path(td)/"receipt";begin(r,BOOT,A,1001,"12020")
   p=r/"receipt.json";x=json.loads(p.read_text());x["generation"]=42;p.write_text(json.dumps(x))
   with self.assertRaisesRegex(CASBlocked,"CHECKSUM"):read(r)
 def test_symlink_denied(self):
  with TemporaryDirectory() as td:
   r=Path(td)/"receipt";begin(r,BOOT,A,1001,"12020")
   p=r/"receipt.json";p.rename(r/"backup.json");p.symlink_to(r/"backup.json")
   with self.assertRaisesRegex(CASBlocked,"SYMLINK"):read(r)
 def test_real_flock_one_winner(self):
  with TemporaryDirectory() as td:
   r=Path(td)/"receipt";begin(r,BOOT,A,1001,"12020")
   def attempt(_):
    try:return nxt(r)["generation"]
    except CASBlocked:return "BLOCKED"
   with ThreadPoolExecutor(max_workers=2) as ex:
    self.assertEqual(sorted(map(str,ex.map(attempt,range(2)))),["2","BLOCKED"])
 def test_even_good_runner_cas_no_physical_release(self):
  from xray.lab.rc40_owner_observability_gate import ExternalWitness,release_decision
  obs=ExternalWitness(BOOT,3,1001,12020,1002,13000,frozenset(),frozenset(),A)
  self.assertEqual(release_decision(obs)["decision"],"HARD_NO_GO_PRODUCTION")
if __name__=="__main__":unittest.main()
