"""Independent RC23 must require *host-received* exact UDP under QEMU restrict=on."""
import pathlib
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNNER=(ROOT/"xray/lab/rc23_mips49_udp_hostfwd_runner.sh").read_text()
GUEST=(ROOT/"xray/lab/rc23_mips49_udp_hostfwd_echo.c").read_text()
class RC23PositiveHostfwd(unittest.TestCase):
 def test_disposable_and_restricted(self):
  self.assertIn('GITHUB_ACTIONS',RUNNER)
  self.assertIn('-netdev user,id=isolated,restrict=on',RUNNER)
  self.assertIn('hostfwd=udp:127.0.0.1:19301-:19301',RUNNER)
 def test_no_xray_or_production(self):
  self.assertNotIn('xray.zip',RUNNER)
  self.assertNotIn('iptables -t mangle -A',RUNNER)
  self.assertNotIn('restrict=off',RUNNER)
 def test_positive_host_udp_mandatory(self):
  self.assertIn('if got!=UDP:',RUNNER)
  self.assertIn('if not results:',RUNNER)
  self.assertIn('HARD_NO_GO_POSITIVE_UDP_RETURN_NOT_WITNESSED',RUNNER)
  self.assertIn('REAL_BYTE_EQUAL_BIDIRECTIONAL_UDP_HOSTFWD_WITH_RESTRICT_ON',RUNNER)
 def test_guest_peer_and_sendto(self):
  self.assertIn('recvfrom(us,buf,sizeof(buf)',GUEST)
  self.assertIn('sendto(us,buf,(size_t)n',GUEST)
  self.assertIn('UDP_SENDTO_EXACT',GUEST)
  self.assertIn('UDP_RX_EXACT',GUEST)
 def test_control_separate(self):
  self.assertIn('TCP_HOSTFWD_POSITIVE_CONTROL',RUNNER)
  self.assertIn('"unconnected","connected"',RUNNER)
 def test_sha_inputs_precede_guest(self):
  self.assertIn('sha256sum -c -',RUNNER)
  self.assertIn('linux-image-4.9.0-13-4kc-malta',RUNNER)
if __name__=="__main__":unittest.main()
