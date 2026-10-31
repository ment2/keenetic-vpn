"""RC28 source checks, not wire-path evidence."""
from pathlib import Path
import unittest
R=Path(__file__).resolve().parents[1]
A=(R/'xray/lab/rc28_dualpath_runner.sh').read_text()
B=(R/'xray/lab/rc28_dualpath_netns.sh').read_text()
C=(R/'xray/lab/rc28_dualpath_guest.sh').read_text()
class Contract(unittest.TestCase):
 def test_pinned_and_isolated(self):
  self.assertIn('sha256sum -c -',A)
  self.assertIn('unshare --net',A)
  self.assertIn('NONEMPTY_NETNS',B)
  self.assertIn('DEFAULT_ROUTE_PRESENT',B)
 def test_two_network_paths(self):
  self.assertIn('restrict=on',B)
  self.assertIn('-netdev tap,id=independent',B)
  self.assertIn('10.77.0.2/24 dev eth1',C)
  self.assertNotIn('restrict=off',B)
 def test_actual_positive_and_negative_separate(self):
  self.assertIn('PRIVATE_TAP_BIDIRECTIONAL_UDP_EXACT_RECEIVED',B)
  self.assertIn('SLIRP_UDP_RETURN_UNPROVEN_DESPITE_TAP_CONTROL',B)
  self.assertIn('received==U and peer==dst',B)
 def test_no_production_release(self):
  self.assertIn('HARD_NO_GO_SLIRP_ORIGINAL_DESTINATION',B)
  self.assertNotIn('PRODUCTION_AUTHORIZED',B)
if __name__=='__main__': unittest.main()
