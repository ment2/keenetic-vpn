"""RC44 disposable only native kernel packet harness contracts."""
import unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]
K=(R/"xray/lab/rc44_tproxy_repair_netns.sh").read_text()
B=(R/"xray/lab/rc44_tproxy_repair_runner.sh").read_text()
P=(R/"xray/lab/rc44_tproxy_packet_witness.py").read_text()
class Scope(unittest.TestCase):
 def test_exact_minimal_two_protocol_batch(self):
  self.assertEqual(K.count("-A XRAY_WIFI -p tcp -j TPROXY"),1)
  self.assertEqual(K.count("-A XRAY_WIFI -p udp -j TPROXY"),1)
  self.assertIn("iptables-restore --noflush",K)
 def test_exact_ruleset_rollback_and_kernel_fail_closed(self):
  self.assertIn('cmp "$W/before.rulelines" "$W/restored.rulelines"',K)
  self.assertIn("-D XRAY_WIFI -p tcp -j TPROXY",K)
  self.assertIn("-D XRAY_WIFI -p udp -j TPROXY",K)
  self.assertIn("iptables -P FORWARD DROP",K)
  self.assertIn("ip6tables -P FORWARD DROP",K)
 def test_real_udp_tcp_socket_packet_witness(self):
  self.assertIn("IP_TRANSPARENT",P)
  self.assertIn("RC44_REAL_TPROXY_UDP_PACKET",P)
  self.assertIn("RC44_REAL_TPROXY_TCP_PACKET",P)
  self.assertIn("RC44_CLIENT_REPAIR_TCP_EXACT_ECHO",P)
 def test_disposable_only_no_keenetic_mutation(self):
  self.assertIn("sudo --preserve-env=GITHUB_ACTIONS,RC44_NINE unshare --net",B)
  self.assertNotIn("ssh root@",K+B+P)
  self.assertNotIn("killall xray",K+B+P)
  self.assertNotIn("PRODUCTION_AUTHORIZED",K+B+P)
if __name__=="__main__":unittest.main()
