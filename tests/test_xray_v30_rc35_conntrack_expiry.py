"""RC35 contract: real Linux4.9 conntrack TIMEOUT negative against held UDP socket."""
from pathlib import Path
import unittest
R=Path(__file__).resolve().parents[1]
G=(R/"xray/lab/rc35_conntrack_expiry_guest.sh").read_text()
H=(R/"xray/lab/rc35_conntrack_expiry_netns.sh").read_text()
RUN=(R/"xray/lab/rc35_conntrack_expiry_runner.sh").read_text()
class RC35Expiry(unittest.TestCase):
 def test_disposable_mips49_and_original_destination(self):
  for m in ("4.9.0-13-4kc-malta","sha256sum -c -","rc34_conntrack_module_pack","unshare --net"):
   self.assertIn(m,RUN)
  self.assertIn("restrict=on",H)
  self.assertIn("10.77.0.3/32 via 10.77.0.2",H)
 def test_actual_timeout_sysctls_readback_in_guest_only(self):
  self.assertIn('nf_conntrack_udp_timeout nf_conntrack_udp_timeout_stream',G)
  self.assertIn('echo 3 >"$path"',G)
  self.assertIn('test "$(/bin/busybox cat "$path")" = 3',G)
 def test_real_conntrack_entry_exists_before_disappearance(self):
  self.assertLess(G.index("RC35_GUEST_REAL_OLD_UDP_CONNTRACK_ENTRY_WITNESSED"),
                  G.index("RC35_GUEST_KERNEL_OLD_UDP_CONNTRACK_EXPIRED"))
  self.assertIn("HARD_NO_GO_INITIAL_CONNTRACK_ENTRY_NEVER_OBSERVED",G)
  self.assertIn("HARD_NO_GO_UDP_CONNTRACK_EXPIRY_NOT_OBSERVED",G)
  self.assertIn('/proc/net/nf_conntrack',G)
 def test_same_client_socket_remains_open_until_after_timeout(self):
  self.assertIn("with udp_sock(0) as idle_udp",H)
  self.assertIn('idle_udp.getsockname()[1]==port',H)
  self.assertIn('udpecho(idle_udp,"OLD_BEFORE_EXPIRY")',H)
  self.assertIn('udpecho(idle_udp,"OLD_AFTER_EXPIRY_NO_CUTOVER")',H)
 def test_no_unsafe_owner_cutover_and_two_process_ticks(self):
  self.assertIn("RC35_GUEST_FAIL_CLOSED_NO_NEW_CANDIDATE_TPROXY_RULES",G)
  self.assertIn('grep -c -- \'-j TPROXY\'',G)
  self.assertIn('= 2',G)
  self.assertIn('old_ticks',G)
  self.assertIn('new_ticks',G)
  self.assertNotIn("22345 --tproxy-mark",G)
 def test_false_ownership_confidence_forbidden(self):
  self.assertIn("CANNOT independently prove the original internal",G)
  self.assertIn("HARD_NO_GO_NO_COMPLETE_XRAY_UDP_OWNER_OR_ATOMIC_FREEZE",G)
  self.assertNotIn("PRODUCTION_AUTHORIZED",G+H+RUN)
if __name__=="__main__":unittest.main()
