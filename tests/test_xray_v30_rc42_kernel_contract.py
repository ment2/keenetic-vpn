"""RC42 source gates for disposable nft kernel DROP negative packet witness."""
from pathlib import Path
import unittest
R=Path(__file__).resolve().parents[1]
A=(R/"xray/lab/rc42_kernel_freeze_netns.sh").read_text()
B=(R/"xray/lab/rc42_kernel_freeze_runner.sh").read_text()
P=(R/"xray/lab/rc42_netns_udp_endpoint.py").read_text()
J=(R/"xray/lab/rc42_fsync_generation_cas.py").read_text()
class Contract(unittest.TestCase):
 def test_netns_no_default_gateway(self):
  for k in ("unshare --net","nsenter -t", "ip -4 route show default"):self.assertIn(k,A)
  self.assertIn("sudo unshare --net",B)
 def test_real_nft_packet_drop_and_counter(self):
  for k in ("nft -f -","type filter hook input priority -100","udp dport 19542 counter drop",
            "nft -a list chain", "RC42_REAL_KERNEL_NFT_DROP_PACKET_TIMEOUT"):self.assertIn(k,A)
 def test_drop_is_not_buffered_freeze(self):
  self.assertIn("RC42_HARD_NO_GO_DROP_IS_NOT_BUFFERED_ATOMIC_SESSION_FREEZE",A)
  self.assertNotIn("XRAY_SESSION_MIGRATED",A+B)
 def test_actual_inode_cookie(self):
  self.assertIn("os.fstat(s.fileno()).st_ino",P)
  self.assertIn("getsockopt(socket.SOL_SOCKET,57,8)",P)
  self.assertIn("RC42_CLIENT_FROZEN_PACKET_TIMED_OUT_IN_REAL_KERNEL",P)
 def test_runner_fsync_is_not_hardware(self):
  for x in ("fcntl.flock","os.fsync(f.fileno())","os.replace(tmp,root","os.fsync(d)"):
   self.assertIn(x,J)
  self.assertIn("EPHEMERAL",J)
 def test_exact_nft_rollback_before_after(self):
  self.assertIn('cmp "$W/original.nft" "$W/restored.nft"',A)
  self.assertIn("RC42_REAL_KERNEL_ORIGINAL_RULESET_EXACTLY_RESTORED",A)
 def test_no_remote_router_control(self):
  for x in ("killall xray","ssh root@","StrictHostKeyChecking=no","PRODUCTION_AUTHORIZED"):
   self.assertNotIn(x,A+B+P+J)
if __name__=="__main__":unittest.main()
