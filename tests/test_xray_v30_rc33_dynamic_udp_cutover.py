"""RC33 real dynamic AF_PACKET UDP ownership before dual-Xray MIPS cutover."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
RUN=(ROOT/"xray/lab/rc33_dynamic_udp_first_tproxy_runner.sh").read_text()
G=(ROOT/"xray/lab/rc33_dynamic_udp_first_tproxy_guest.sh").read_text()
H=(ROOT/"xray/lab/rc33_dynamic_udp_first_tproxy_netns.sh").read_text()
C=(ROOT/"xray/lab/rc33_udp_flow_observer.c").read_text()
class DynamicUDP(unittest.TestCase):
 def test_real_mips49_guest_observer_packet_socket(self):
  for x in ("AF_PACKET","SOCK_RAW","ETH_P_IP","if_nametoindex","IPPROTO_UDP","sockaddr_ll"):
   self.assertIn(x,C)
  self.assertIn("mipsel-linux-gnu-gcc -static",RUN)
  self.assertIn("rc33_udp_flow_observer.c",RUN)
  self.assertIn("4.9.0-13-4kc-malta",RUN)
  self.assertIn("sha256sum -c -",RUN)
 def test_full_flow_identity_and_bound(self):
  for x in ("ip->saddr","ip->daddr","sport","dport","eth1","MAXFLOWS","INCOMPLETE_OLD_FLOW_INVENTORY"):
   self.assertIn(x,C)
  self.assertIn("BOOT_ID_INVALID",C)
  self.assertIn("generation=1",C)
  self.assertIn("fsync(fileno(f))",C)
 def test_actual_random_source_ports_not_hardcoded(self):
  self.assertIn("udp_sock(0) as old_udp_a",H)
  self.assertIn("udp_sock(0) as old_udp_b",H)
  self.assertIn("RUNTIME_DISCOVERED_EPHEMERAL_UDP_SOURCE_PORTS",H)
  self.assertIn("OLD_A_AFTER_ROLLBACK",H)
  self.assertIn("OLD_B_AFTER_ROLLBACK",H)
  self.assertNotIn("--sport 21112",G)
 def test_precutover_boot_generation_cas(self):
  self.assertIn("/proc/sys/kernel/random/boot_id",G)
  self.assertIn('generation=1 interface=eth1 count=2',G)
  self.assertIn('BOOT_GENERATION_FLOW_CAS_MISMATCH',G)
  self.assertIn('STALE_CAS_ROLLBACK',G)
  self.assertIn("old_ticks",G)
  self.assertIn("new_ticks",G)
 def test_dynamic_pin_before_broad_udp(self):
  self.assertIn("flow_count=$((flow_count+1))",G)
  self.assertIn("--sport \"$sport\"",G)
  self.assertIn("HARD_NO_GO_FOREIGN_OR_MODIFIED_5TUPLE",G)
  self.assertIn("positive[5]",G)
  self.assertIn("flow_count+3",G)
 def test_disposable_and_no_generic_authorization(self):
  self.assertIn("restrict=on",H)
  self.assertIn("unshare --net",RUN)
  self.assertIn("NO_DEFAULT",H)
  self.assertIn("HARD_NO_GO_DYNAMIC_UDP_5TUPLE_CAS_PRIVILEGED_LEGACY_FENCING_PHYSICAL",H)
  self.assertNotIn("PRODUCTION_AUTHORIZED",RUN+G+H)
if __name__=="__main__":unittest.main()
