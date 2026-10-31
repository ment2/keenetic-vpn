"""RC15 package pins are a read-only prereq, never packet-path evidence."""
import json,re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class RC15ArchivePins(unittest.TestCase):
 def test_three_sha_pins_are_distinct_and_exact_format(self):
  p=json.loads((ROOT/"xray/staging/v30-rc15-mipsel-userland-package-pins.json").read_text())
  self.assertEqual(len(p["packages"]),3)
  self.assertEqual({x["name"] for x in p["packages"]},{"iptables","iproute2","busybox-static"})
  for x in p["packages"]:
   self.assertTrue(re.fullmatch("[0-9a-f]{64}",x["sha256"]))
   self.assertEqual(x["arch"],"mipsel")
  self.assertEqual(p["decision"],"HARD_NO_GO_PRODUCTION")
  self.assertFalse(p["production_authorized"])
  self.assertFalse(p["foreign_binaries_executed"])
  self.assertFalse(p["dynamic_library_closure_verified"])
  self.assertFalse(p["real_tcp_udp_mips_packet_path_verified"])
  self.assertFalse(p["hardware_fencing_boot_rescue_verified"])
  self.assertEqual(p["router_jobs"],0)
 def test_workflow_rejects_unpinned_archive_bytes(self):
  p=json.loads((ROOT/"xray/staging/v30-rc15-mipsel-userland-package-pins.json").read_text())
  w=(ROOT/".github/workflows/xray-v30-rc15-mips-userland-discovery.yml").read_text()
  self.assertIn("sha256sum -c -",w)
  self.assertIn("xtables-multi",w)
  for package in p["packages"]:
   self.assertIn(package["sha256"],w)
  self.assertNotIn("GITHUB_TOKEN:",w)
  self.assertNotIn("workflow_dispatch:\n    inputs:",w)
if __name__=="__main__":unittest.main()
