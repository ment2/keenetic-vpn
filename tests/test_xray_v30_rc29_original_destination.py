"""Original destination RC29 must use real Xray and disjoint backend network namespace."""
import json
from pathlib import Path
import unittest
R=Path(__file__).resolve().parents[1]
RUN=(R/"xray/lab/rc29_original_runner.sh").read_text()
HOST=(R/"xray/lab/rc29_original_netns.sh").read_text()
GUEST=(R/"xray/lab/rc29_original_guest.sh").read_text()
class Original(unittest.TestCase):
 def test_no_redirect_and_exact_original_dest(self):
  marker='cat >"$W/initramfs/etc/xray.json" <<\'JSON\'\n'
  self.assertIn(marker,RUN)
  obj=json.loads(RUN.split(marker)[1].split("\nJSON\n")[0])
  self.assertEqual(obj["outbounds"][0]["protocol"],"freedom")
  self.assertNotIn("redirect",str(obj))
  self.assertTrue(obj["inbounds"][0]["settings"]["followRedirect"])
 def test_restricted_private_netns_and_ip(self):
  self.assertIn("unshare --net",RUN)
  self.assertIn("restrict=on",HOST)
  self.assertIn("v29b netns",HOST)
  self.assertIn("10.77.0.3/32 via 10.77.0.2",HOST)
  self.assertIn("eth1",GUEST)
  self.assertNotIn("restrict=off",HOST)
 def test_true_tcp_udp_and_counter_witnesses(self):
  self.assertIn("REAL_MIPS_XRAY_TCP_ORIGINAL_DEST_RESPONSE",HOST)
  self.assertIn("REAL_MIPS_XRAY_UDP_ORIGINAL_DEST_RESPONSE",HOST)
  self.assertIn("ORIGINAL_DEST_UDP_ECHO_EXACT",HOST)
  self.assertIn("REAL_XRAY_ORIGINAL_DEST_TPROXY_COUNTERS_POSITIVE",GUEST)
 def test_no_production_approval(self):
  self.assertIn("HARD_NO_GO_SLIRP_HOSTFWD_LEGACY_ROOT_FENCING_PHYSICAL_RESCUE",HOST)
  self.assertNotIn("PRODUCTION_AUTHORIZED",HOST)
if __name__=="__main__":unittest.main()
