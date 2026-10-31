"""RC30 original foreign destination no-direct-fallback evidence contract, disposable only."""
from pathlib import Path
import unittest
R=Path(__file__).resolve().parents[1]
RUN=(R/'xray/lab/rc30_postdeath_runner.sh').read_text()
NET=(R/'xray/lab/rc30_postdeath_netns.sh').read_text()
GUEST=(R/'xray/lab/rc30_postdeath_guest.sh').read_text()
BACK=(R/'xray/lab/rc30_postdeath_backend.py').read_text()
class RC30(unittest.TestCase):
 def test_disposable_and_real_xray_no_redirect(self):
  self.assertIn('GITHUB_ACTIONS',RUN)
  self.assertIn('unshare --net',RUN)
  self.assertIn('"settings":{}',RUN)
  self.assertIn('restrict=on',NET)
 def test_direct_child_verified_before_owned_signal(self):
  for x in ('/proc/$xr/stat','start_ticks','/proc/sys/kernel/random/boot_id','kill -TERM "$xr"','wait "$xr"'):
   if x=='start_ticks': self.assertIn('start_ticks',GUEST)
   else: self.assertIn(x,GUEST)
  self.assertNotIn('killall',GUEST)
 def test_backend_live_through_canary(self):
  self.assertIn('NO_TCP_UDP_POSTDEATH_CANARY_DELIVERED_IN_BOUNDED_WINDOW',BACK)
  self.assertIn('HARD_NO_GO_POSTDEATH_TCP_REACHED_REAL_BACKEND',BACK)
  self.assertIn('HARD_NO_GO_POSTDEATH_UDP_REACHED_REAL_BACKEND',BACK)
  self.assertIn('NO_TCP_CANARY_REPLY_POST_XRAY_DEATH',NET)
  self.assertIn('NO_UDP_CANARY_REPLY_POST_XRAY_DEATH',NET)
 def test_real_packet_counters_required(self):
  self.assertIn('after" -gt "$before',GUEST)
  self.assertIn('REAL_TCP_UDP_TPROXY_POSTDEATH_COUNTERS_INCREASED',GUEST)
 def test_release_stays_blocked(self):
  self.assertIn('HARD_NO_GO_SLIRP_HOSTFWD_LEGACY_ROOT_FENCING_PHYSICAL_RESCUE',NET)
  self.assertNotIn('PRODUCTION_AUTHORIZED',NET)
if __name__=="__main__":unittest.main()
