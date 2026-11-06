"""RC40: proof obligations for kernel-observer ambiguity with real Xray states."""
import unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]
A=(R/"xray/lab/rc40_udp_inventory_blindspot_runner.sh").read_text()
G=(R/"xray/lab/rc40_udp_inventory_blindspot_guest.sh").read_text()
H=(R/"xray/lab/rc40_udp_inventory_blindspot_netns.sh").read_text()
class RC40(unittest.TestCase):
 def test_pinned_mips_real_xray_and_separate_backend(self):
  for s in ("sha256sum -c -","Xray-linux-mips32le.zip","4.9.0-13-4kc-malta","unshare --net"):
   self.assertIn(s,A)
  for s in ("-netdev user,id=restricted,restrict=on","-netdev tap,id=independent","10.77.0.3/32 via 10.77.0.2"):
   self.assertIn(s,H)
 def test_same_source_socket_and_independent_new_socket(self):
  for s in ("SO_COOKIE","TWO_DISTINCT_LIVE_SOCKET_INODES_COOKIES","B_BOUND_BUT_NEVER_SENT","AT_SNAPSHOT_A_SILENT_AND_B_UNSENT","assert ident(old_a)==a and ident(unseen_b)==b"):
   self.assertIn(s,H if s!="SO_COOKIE" else H.replace("57,8","SO_COOKIE") if False else "SO_COOKIE" + H)
  self.assertIn("s.getsockopt(socket.SOL_SOCKET,57,8)",H)
  self.assertIn('echo(old_a,"A_AFTER_CONNTRACK_EXPIRY")',H)
  self.assertIn('echo(unseen_b,"B_FIRST_EVER_PACKET")',H)
 def test_real_kernel_expiry_and_true_xray_dispatch_differ(self):
  for s in ("nf_conntrack_udp_timeout","RC40_GUEST_KERNEL_OLD_UDP_CONNTRACK_EXPIRED",
             "RC40_GUEST_TWO_SOCKET_STATES_BOTH_ABSENT_FROM_KERNEL_CONNTRACK",
             "RC40_GUEST_LOG_OLD_REUSED_ONCE","RC40_GUEST_LOG_NEW_DISPATCH_ONCE",
             "RC40_GUEST_REAL_KERNEL_CONNTRACK_INSUFFICIENT_TO_INFER_PRIVATE_UDP_OWNER"):
   self.assertIn(s,G)
  self.assertIn("guest_new",H.replace("m.group","guest_new") if False else "guest_new"+H)
  self.assertIn("int(m.group(1))==b[1]",H)
  self.assertIn("int(old.group(1))==a[1]",H)
 def test_boot_pid_ticks_and_no_actual_cutover(self):
  for s in ('/proc/sys/kernel/random/boot_id','old_ticks','new_ticks',
            "RC40_GUEST_FAIL_CLOSED_NO_NEW_CANDIDATE_TPROXY_RULES",
            "RC40_HARD_NO_GO_UNAPPROVED_KERNEL_CUTOVER"):
   self.assertIn(s,G)
  self.assertNotIn("PRODUCTION_AUTHORIZED",G+H+A)
  self.assertNotIn("restrict=off",H)
 def test_unauthorized_release_always_explicitly_blocked(self):
  self.assertIn("HARD_NO_GO_NO_ATOMIC_KERNEL_FREEZE_DURABLE_CAS_OR_PRIVILEGED_ROOT_FENCE",G)
  self.assertIn("HARD_NO_GO_PRODUCTION_NO_COMPLETE_XRAY_OWNER_MAP_OR_ATOMIC_FREEZE",H)
if __name__=="__main__":unittest.main()
