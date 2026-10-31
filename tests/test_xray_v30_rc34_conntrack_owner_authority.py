"""Even positive Linux conntrack cannot substitute complete Xray UDP owner map."""
import unittest
from dataclasses import replace
from xray.lab.rc34_conntrack_owner_authority_gate import Identity,Ownership,Evidence,evaluate
BOOT="00000000-1111-2222-3333-444444444444"
A=Identity("10.77.0.1",38381,"10.77.0.3",19301,"udp","eth1")
B=Identity("10.77.0.1",45220,"10.77.0.3",19301,"udp","eth1")
def fixture():
 return Evidence(BOOT,5,(A,B),
     (Ownership(A,53,100,5,BOOT,10000),Ownership(B,53,100,5,BOOT,10001)),
     (A,B),(A,B),True,True,True,True,True,True)
class RC34Authority(unittest.TestCase):
 def test_full_synthetic_is_never_production(self):
  r=evaluate(fixture())
  self.assertEqual(r["decision"],"SYNTHETIC_CONTRACT_ONLY")
  self.assertFalse(r["production_authorized"])
  self.assertFalse(r["all_old_udp_sessions_proven"])
  self.assertEqual(r["router_commands"],())
 def test_kernel_conntrack_idle_but_no_xray_session_owner(self):
  r=evaluate(replace(fixture(),xray_session_inventory=()))
  self.assertIn("XRAY_INTERNAL_UDP_SESSION_OWNER_INVENTORY_UNAVAILABLE",r["reasons"])
 def test_conntrack_timeout_drops_quiet_old_flow(self):
  r=evaluate(replace(fixture(),kernel_conntrack=(A,)))
  self.assertIn("KERNEL_CONNTRACK_MISSED_OR_EXPIRED_UDP_ASSOCIATION",r["reasons"])
 def test_kernel_conntrack_cannot_name_interface_or_owner(self):
  r=evaluate(replace(fixture(),kernel_conntrack=(replace(A,interface=""),B)))
  self.assertIn("UDP_IDENTITY_INVALID_OR_MISSING_INTERFACE",r["reasons"])
  r=evaluate(replace(fixture(),xray_session_inventory=(replace(fixture().xray_session_inventory[0],socket_cookie=0),fixture().xray_session_inventory[1])))
  self.assertIn("SESSION_OWNER_PID_START_BOOT_GENERATION_INVALID",r["reasons"])
 def test_stale_boot_generation_pid_ticks(self):
  for change in ({"boot_id":"different"}, {"generation":6}):
   r=evaluate(replace(fixture(),**change))
   self.assertIn("SESSION_OWNER_PID_START_BOOT_GENERATION_INVALID",r["reasons"])
  old=fixture().xray_session_inventory
  r=evaluate(replace(fixture(),xray_session_inventory=(replace(old[0],start_ticks=0),old[1])))
  self.assertIn("SESSION_OWNER_PID_START_BOOT_GENERATION_INVALID",r["reasons"])
 def test_each_atomic_fencing_gate_independent(self):
  for name in ("no_packets_allowed_during_inventory_commit","durable_generation_cas_ack",
               "exact_kernel_owner_cas_ack","independent_root_descendant_fence_ack",
               "original_destination_preserved","old_tcp_udp_after_rollback"):
   with self.subTest(gate=name):
    r=evaluate(replace(fixture(),**{name:False}))
    self.assertIn("MISSING_ATOMIC_ACCEPTANCE:"+name,r["reasons"])
if __name__=="__main__":unittest.main()
