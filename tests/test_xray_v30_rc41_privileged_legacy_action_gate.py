"""RC41 mutation tests for each of seven real versioned privileged legacy actors."""
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import unittest
from xray.lab.rc41_privileged_legacy_action_gate import (
 ROOT,SOURCES,EXECUTABLE_CAPABILITIES,LegacyDescendantClaim,audit,
)
BOOT="00000000-1111-2222-3333-444444444444"
def claims():
 return tuple(LegacyDescendantClaim(a,BOOT,9,100+i,20,222+i,200+i,"b"*64,
         True,True,True) for i,a in enumerate(SOURCES))
class RC41LegacySourceNegative(unittest.TestCase):
 def test_all_seven_versioned_sources_and_distinct_behaviors(self):
  x=audit()
  self.assertEqual(len(x["versioned_files_sha256"]),7)
  self.assertEqual(set(x["versioned_files_sha256"]),set(SOURCES))
  self.assertEqual(set(EXECUTABLE_CAPABILITIES),set(SOURCES))
  self.assertTrue(all(len(x["versioned_files_sha256"][a]["sha256"])==64 for a in SOURCES))
  self.assertEqual(x["decision"],"HARD_NO_GO_PRODUCTION")
  self.assertEqual(x["router_actions"],())
 def test_s97_global_killall_distinct_from_hourly_staging(self):
  a=(ROOT/SOURCES["S97xray"]).read_text()
  b=(ROOT/SOURCES["xray-safe-hourly.sh"]).read_text()
  self.assertIn("killall xray",a)
  self.assertIn("STAGED_ONLY:",b)
  self.assertNotIn('"$SERVICE" stop',b)
  self.assertNotIn('"$SERVICE" start',b)
 def test_route_writer_and_recovery_cron_are_conditional(self):
  s=(ROOT/SOURCES["xray-wifi-rules.sh"]).read_text()
  c=(ROOT/SOURCES["xray-fc-cron-guard.sh"]).read_text()
  self.assertIn('ip route replace local default',s)
  self.assertIn("xray-fc-guard-enabled",c)
  self.assertIn("xray-fc-recover.sh",c)
 def test_missing_versioned_actor_fail_closed(self):
  with TemporaryDirectory() as t:
   r=audit(root=Path(t))
   self.assertIn("VERSIONED_ROOT_ACTOR_SOURCE_MISSING:S97xray",r["reason_codes"])
   self.assertFalse(r["privileged_root_fence_proven"])
 def test_mutate_each_capability_fail_closed(self):
  for actor,p in SOURCES.items():
   with self.subTest(actor=actor),TemporaryDirectory() as t:
    q=Path(t)/p
    q.parent.mkdir(parents=True,exist_ok=True)
    q.write_text("no unsafe capability executable evidence")
    r=audit(root=Path(t))
    self.assertIn("LEGACY_ACTION_CAPABILITY_SOURCE_DRIFT:"+actor,r["reason_codes"])
 def test_missing_claims_for_seven_descendants(self):
  r=audit(expected_boot_id=BOOT,expected_generation=9)
  self.assertIn("SEVEN_LEGACY_ACTOR_DESCENDANT_RECEIPTS_MISSING_OR_DUPLICATE",r["reason_codes"])
 def test_each_independent_kernel_deny_must_be_claimed(self):
  for i,c in enumerate(claims()):
   events=list(claims())
   events[i]=replace(c,independently_kernel_denied=False)
   r=audit(claims=events,expected_boot_id=BOOT,expected_generation=9)
   self.assertIn("ROOT_ACTOR_KERNEL_DENIAL_MISSING:"+c.actor,r["reason_codes"])
 def test_foreign_boot_pid_start_and_cookie_rejected(self):
  c=list(claims())
  c[0]=replace(c[0],boot_id="foreign-boot",start_ticks=0,socket_cookie=0)
  r=audit(claims=c,expected_boot_id=BOOT,expected_generation=9)
  self.assertIn("ROOT_ACTOR_STALE_BOOT_OR_GENERATION:S97xray",r["reason_codes"])
  self.assertIn("ROOT_ACTOR_IDENTITY_OR_SOCKET_COOKIE_MISSING:S97xray",r["reason_codes"])
 def test_escaped_cgroup_and_noncooperative_root(self):
  c=list(claims())
  c[0]=replace(c[0],escaped_cgroup=True)
  r=audit(claims=c,expected_boot_id=BOOT,expected_generation=9)
  self.assertIn("ROOT_ACTOR_CGROUP_PRIVILEGE_BYPASS:S97xray",r["reason_codes"])
 def test_all_synthetic_positive_still_cannot_release(self):
  r=audit(claims=claims(),expected_boot_id=BOOT,expected_generation=9)
  self.assertFalse(r["production_authorized"])
  self.assertFalse(r["privileged_root_fence_proven"])
  self.assertFalse(r["physical_rescue_proven"])
  self.assertFalse(r["kernel_freeze_commit_proven"])
  self.assertIn("NO_ACTUAL_PHYSICAL_PRIVILEGED_ROOT_DESCENDANT_FENCE",r["reason_codes"])
if __name__=="__main__":unittest.main()
