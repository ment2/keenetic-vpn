"""Every privileged actor has an independent negative cutover release contract."""
from dataclasses import replace
import unittest
from xray.lab.rc34_privileged_actor_fencing_gate import RestartAttempt,evaluate
from xray.lab.rc31_privileged_legacy_evidence_gate import SOURCES
BOOT="00000000-1111-2222-3333-444444444444"
KINDS=("killall_xray","rewrite_tproxy","restart_s97","cron_restart","spawn_root","write_xray")
def fixture():
 return tuple(RestartAttempt(a,KINDS[i%len(KINDS)],5,BOOT,501+i,101+i,True,True,True)
              for i,a in enumerate(SOURCES))
class RC34Fencing(unittest.TestCase):
 def test_all_seven_synthetic_fences_do_not_authorize(self):
  r=evaluate(fixture(),boot_id=BOOT,generation=5)
  self.assertEqual(r["decision"],"HARD_NO_GO_PRODUCTION")
  self.assertFalse(r["release_authorized"])
  self.assertFalse(r["live_fencing_proven"])
 def test_each_actor_ignoring_shared_flock_never_passes(self):
  e=fixture()
  for i,p in enumerate(e):
   with self.subTest(actor=p.actor):
    clone=list(e);clone[i]=replace(p,kernel_denied=False)
    r=evaluate(clone,boot_id=BOOT,generation=5)
    self.assertIn("ROOT_ACTION_NOT_INDEPENDENTLY_DENIED:"+p.actor,r["reasons"])
 def test_forged_receipt_and_cgroup_escape_denied(self):
  e=fixture()
  for i,p in enumerate(e):
   for k,v,reason in (
     ("receipt_from_independent_kernel",False,"ROOT_ACTION_NOT_INDEPENDENTLY_DENIED:"),
     ("escaped_cgroup",True,"LEGACY_DESCENDANT_ESCAPED_CGROUP:"),
     ("start_ticks",0,"PID_START_TICKS_UNTRUSTED:"),
     ("generation",4,"STALE_BOOT_OR_GENERATION:"),
     ("boot_id","other","STALE_BOOT_OR_GENERATION:")):
    with self.subTest(actor=p.actor,mutation=k):
     changed=list(e);changed[i]=replace(p,**{k:v})
     r=evaluate(changed,boot_id=BOOT,generation=5)
     self.assertIn(reason+p.actor,r["reasons"])
 def test_omitted_actor_unknown_and_reparented_process(self):
  e=fixture()
  r=evaluate(e[:-1],boot_id=BOOT,generation=5)
  self.assertIn("SEVEN_ROOT_ENTRYPOINTS_NOT_COVERED",r["reasons"])
  r=evaluate(e+(replace(e[0],actor="rogue-orphan",pid=1),),boot_id=BOOT,generation=5)
  self.assertIn("UNKNOWN_LEGACY_ACTOR:rogue-orphan",r["reasons"])
  self.assertIn("PID_START_TICKS_UNTRUSTED:rogue-orphan",r["reasons"])
 def test_never_provides_production_actions(self):
  r=evaluate(fixture(),boot_id=BOOT,generation=5)
  self.assertEqual(r["router_actions"],())
  self.assertIn("ROOT_CGROUP_V1_ESCAPE_NOT_CONTAINED_ON_HARDWARE",r["reasons"])
if __name__=="__main__":unittest.main()
