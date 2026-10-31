"""RC31 adversarial release-fence regression. No subprocess/network calls."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from dataclasses import replace
from xray.lab.rc31_privileged_legacy_evidence_gate import (
 SOURCES,ROOT,ProcessWitness,PhysicalEvidence,evaluate,snapshot_hashes,
 ROOT_ESCAPE_OBSERVED,
)
class RC31(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.hashes=snapshot_hashes()
 def test_exact_seven_snapshots_and_digest_readback(self):
  self.assertEqual(len(SOURCES),7)
  self.assertEqual(len(self.hashes),7)
  ev=evaluate(expected_hashes=self.hashes)
  self.assertEqual(ev["snapshot_count"],7)
  self.assertEqual(set(ev["source_snapshots"]),set(SOURCES))
  self.assertIn(ROOT_ESCAPE_OBSERVED,ev["reasons"])
 def test_no_liveness_claim_even_all_physical_synthetic_true(self):
  ev=evaluate(expected_hashes=self.hashes,boot_id="00000000-1111-2222-3333-444444444444",
    generation=9,physical=PhysicalEvidence(*([True]*8)))
  self.assertEqual(ev["decision"],"HARD_NO_GO_PRODUCTION")
  self.assertFalse(ev["production_authorized"])
  self.assertFalse(ev["live_fencing_proven"])
  self.assertFalse(ev["hardware_accepted"])
  self.assertEqual(ev["router_actions"],())
 def test_missing_snapshot_and_drift_hard_no_go(self):
  with TemporaryDirectory() as tmp:
   ev=evaluate(Path(tmp),expected_hashes=self.hashes)
   self.assertEqual(ev["snapshot_count"],0)
   self.assertIn("MISSING_VERSIONED_ACTOR:S97xray",ev["reasons"])
  forged=dict(self.hashes);forged["S97xray"]="f"*64
  ev=evaluate(expected_hashes=forged)
  self.assertIn("SNAPSHOT_SHA_MISSING_OR_DRIFTED:S97xray",ev["reasons"])
 def test_missing_evidence_default_fails_closed(self):
  ev=evaluate()
  for reason in ("ACTOR_HASH_INVENTORY_UNSEALED","BOOT_ID_UNVERIFIED",
       "DURABLE_GENERATION_UNVERIFIED","NO_ROUTER_PROCESS_OR_CHILD_IDENTITY_READBACK",
       "PHYSICAL_HARD_NO_GO:physical_usb_removed_rescue_boot_proven"):
   self.assertIn(reason,ev["reasons"])
 def test_real_seven_actors_do_not_have_verified_cas(self):
  ev=evaluate(expected_hashes=self.hashes)
  for actor in SOURCES:
   self.assertIn("NO_VERIFIED_SHARED_CAS_AND_PID_STARTTICKS:"+actor,ev["reasons"])
 def test_stale_pid_and_unknown_root_descendant(self):
  p=ProcessWitness(pid=551,ppid=1,start_ticks=30,
    boot_id="00000000-1111-2222-3333-444444444444",
    executable_sha256="a"*64,generation=9,cgroup="/legacy",privileged=True,socket_inodes=(77,))
  ev=evaluate(expected_hashes=self.hashes,boot_id=p.boot_id,generation=9,
    before=(p,),after=(replace(p,start_ticks=31),))
  for k in ("BEFORE_PID_START_BOOT_EXE_INVALID","BEFORE_ROOT_OR_UNFENCED_CGROUP",
    "AFTER_PID_REUSE_OR_STARTTICKS_CHANGED","LIVE_LEGACY_DESCENDANTS_OR_ORPHANS_REMAIN"):
   self.assertIn(k,ev["reasons"])
 def test_duplicate_socket_and_stale_generation(self):
  p=ProcessWitness(99,11,100,"00000000-1111-2222-3333-444444444444",
     "a"*64,8,"/legacy",False,(5,5))
  ev=evaluate(expected_hashes=self.hashes,boot_id=p.boot_id,generation=9,before=(p,))
  self.assertIn("BEFORE_SOCKET_INODE_UNTRUSTED",ev["reasons"])
  self.assertIn("BEFORE_GENERATION_CAS_MISMATCH",ev["reasons"])
if __name__=="__main__":unittest.main()
