"""RC35: fail closed on idle UDP, Xray owner map, stale generation and root bypass."""
from dataclasses import replace
from threading import Barrier,Thread
import unittest
from xray.lab.rc35_freeze_cas_disposable_model import Flow,Witness,HandoverModel,UnsafeHandover
A=Flow("eth1","10.77.0.1",39001,"10.77.0.3",19301)
B=Flow("eth1","10.77.0.1",39002,"10.77.0.3",19301)
BOOT="00000000-1111-2222-3333-444444444444"
def witness():
 flows=frozenset((A,B))
 return Witness(BOOT,10,flows,flows,flows,True,True,True)
def model():
 return HandoverModel(BOOT,10,frozenset((A,B)))
class RC35CAS(unittest.TestCase):
 def test_simulation_only_never_production(self):
  c=model();p=c.prepare(witness())
  self.assertEqual(c.commit(p,exact_kernel_owner_receipt=True,old_socket_bytes_preserved=True),11)
  self.assertEqual(c.rollback(boot_id=BOOT,expected_generation=11,
                  original_rules_restored=True,old_socket_bytes_preserved=True),12)
  self.assertEqual(c.phase,"OLD_OWNER")
  self.assertFalse(c.production_authorized)
 def test_expired_kernel_idle_flow_refuses_before_freeze(self):
  c=model()
  with self.assertRaisesRegex(UnsafeHandover,"SILENT_OR_EXPIRED"):
   c.prepare(replace(witness(),kernel_flows=frozenset((A,))))
  self.assertEqual((c.generation,c.phase),(10,"OLD_OWNER"))
 def test_missing_xray_internal_owner_refuses(self):
  c=model()
  with self.assertRaisesRegex(UnsafeHandover,"SILENT_OR_EXPIRED"):
   c.prepare(replace(witness(),xray_owned_flows=frozenset()))
 def test_separate_atomic_gates_all_required(self):
  for field in ("kernel_freeze_receipt","complete_xray_owner_inventory_receipt","independent_root_fence_receipt"):
   with self.subTest(field=field):
    c=model()
    with self.assertRaisesRegex(UnsafeHandover,"MISSING_KERNEL_FREEZE"):
     c.prepare(replace(witness(),**{field:False}))
    self.assertEqual(c.phase,"OLD_OWNER")
 def test_stale_boot_generation_and_mutated_client(self):
  for w in (replace(witness(),boot_id="rebooted"),replace(witness(),generation=9),
            replace(witness(),active_client_flows=frozenset((A,)))):
   c=model()
   with self.assertRaises(UnsafeHandover):c.prepare(w)
 def test_commit_requires_both_ack_and_old_socket_bytes(self):
  for owner,old in ((False,True),(True,False)):
   c=model();p=c.prepare(witness())
   with self.assertRaisesRegex(UnsafeHandover,"KERNEL_OWNER_ACK"):
    c.commit(p,exact_kernel_owner_receipt=owner,old_socket_bytes_preserved=old)
   self.assertEqual(c.phase,"FROZEN")
 def test_rollback_rejects_wrong_boot_generation_and_missing_restore(self):
  for kwargs in ({"boot_id":"wrong"},{"expected_generation":9},{"original_rules_restored":False},
                 {"old_socket_bytes_preserved":False}):
   c=model();p=c.prepare(witness())
   c.commit(p,exact_kernel_owner_receipt=True,old_socket_bytes_preserved=True)
   args=dict(boot_id=BOOT,expected_generation=11,original_rules_restored=True,old_socket_bytes_preserved=True)
   args.update(kwargs)
   with self.assertRaises(UnsafeHandover):c.rollback(**args)
   self.assertEqual(c.phase,"NEW_FLOWS_CANDIDATE_OLD_PINNED")
 def test_concurrent_prepare_single_owner(self):
  c=model();barrier=Barrier(3);res=[]
  def attempt():
   barrier.wait()
   try:res.append(("ok",c.prepare(witness())))
   except UnsafeHandover:res.append(("blocked",None))
  tt=[Thread(target=attempt),Thread(target=attempt)]
  for t in tt:t.start()
  barrier.wait()
  for t in tt:t.join(timeout=3);self.assertFalse(t.is_alive())
  self.assertEqual(sorted(x[0] for x in res),["blocked","ok"])
  self.assertEqual(c.phase,"FROZEN")
if __name__=="__main__":unittest.main()
