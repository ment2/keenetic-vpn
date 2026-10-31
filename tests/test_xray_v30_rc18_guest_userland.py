"""RC18 source safety: SHA pin all MIPS packages and hard NO-GO for packet path."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class RC18Source(unittest.TestCase):
 def test_guest_execution_is_disposable_and_no_packet_claim(self):
  s=(ROOT/"xray/lab/rc18_mips49_guest_userland_runner.sh").read_text()
  c=(ROOT/"xray/lab/rc18_mips49_guest_userland_init.c").read_text()
  self.assertIn("-net none",s)
  self.assertEqual(s.count("\nfetch "),7) # exactly seven pinned archive packages
  self.assertIn("sha256sum -c -",s)
  self.assertIn("execv(binary,args)",c)
  self.assertIn("waitpid(pid,&status,0)",c)
  self.assertIn("HARD_NO_GO_TCP_UDP_PACKET_PATH_NOT_EXECUTED",s)
  self.assertNotIn("iptables -A",s)
  self.assertNotIn("ssh ",s)
if __name__=="__main__":unittest.main()
