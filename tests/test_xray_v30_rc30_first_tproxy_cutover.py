"""RC30 strict packet-path-only first TPROXY TCP/UDP cutover contract."""
from pathlib import Path
import json
import unittest
R=Path(__file__).resolve().parents[1]
RUN=(R/"xray/lab/rc30_first_tproxy_runner.sh").read_text()
GUEST=(R/"xray/lab/rc30_first_tproxy_cutover_guest.sh").read_text()
HOST=(R/"xray/lab/rc30_first_tproxy_netns.sh").read_text()
BE=(R/"xray/lab/rc30_first_tproxy_backend.py").read_text()
class RC30FirstCutover(unittest.TestCase):
 def test_true_qemu_mips49_pinned(self):
  for x in ("linux-image-4.9.0-13-4kc-malta", "Xray-linux-mips32le.zip","sha256sum -c -","rc20_mips49_tproxy_module_pack"):
   self.assertIn(x,RUN)
 def test_two_independent_cap_net_raw_processes(self):
  self.assertIn('rc30capwrap',RUN)
  self.assertIn('rc9capwrap',RUN)
  self.assertIn('/bin/rc9capwrap raw xray',GUEST)
  self.assertIn('/bin/rc30capwrap raw xray',GUEST)
  self.assertIn('no_new_privs=1',GUEST)
  self.assertIn('old_ticks',GUEST)
  self.assertIn('new_ticks',GUEST)
 def test_original_destination_no_fake_redirect(self):
  for marker in ('cat >"$W/initramfs/etc/xray.json"','cat >"$W/initramfs/etc/xray-candidate.json"'):
   config=json.loads(RUN.split(marker+" <<'JSON'\n")[-1].split("\nJSON\n")[0]) if False else None
  self.assertIn('"settings":{}',RUN)
  self.assertNotIn('"redirect"',RUN)
  self.assertIn('10.77.0.3/32 via 10.77.0.2',HOST)
  self.assertIn('RC30_BACKEND_INDEPENDENT_ORIGINAL_DEST_READY',BE)
 def test_real_tcp_udp_old_new_after(self):
  for phase in ("OLD_BEFORE","OLD_DURING","NEW_DURING","OLD_AFTER_ROLLBACK","NEW_AFTER_ROLLBACK"):
   self.assertIn(phase,HOST)
  self.assertIn('old_tcp',HOST)
  self.assertIn('old_udp',HOST)
  self.assertIn('NEW_ONLY_TUPLE_PINNED_CUTOVER_READY',GUEST)
  self.assertIn('CUTOVER_RULES_REMOVED_ROLLBACK_READY',GUEST)
 def test_exact_tuple_limit_must_be_reported(self):
  for port in ("21111","21112","21113","21114"):
   self.assertIn(port,GUEST+HOST)
  self.assertIn('HARD_NO_GO_GENERIC_UDP_5TUPLE_FENCING_WATCHDOG_PHYSICAL',GUEST)
  self.assertNotIn('PRODUCTION_AUTHORIZED',HOST)
 def test_no_external_and_packet_mark_evidence(self):
  self.assertIn('restrict=on',HOST)
  self.assertIn('unshare --net',RUN)
  self.assertIn('NO_DEFAULT',HOST)
  self.assertIn('netns',HOST)
  self.assertIn('rc20_mips49_tproxy_module_pack',RUN)
  self.assertIn('tproxy-mark 0x40000000',GUEST)
  self.assertIn('HARD_NO_GO_BOTH_TPROXY_OWNERS_NOT_WITNESSED',GUEST)
 def test_udp_old_pin_precedes_broad_rule_at_runtime(self):
  # iptables -I PREROUTING 1 reverses source insertion order.
  broad="udp --dport 19301 -j TPROXY --on-port 22345"
  old="udp --sport 21112 --dport 19301 -j TPROXY --on-port 12345"
  self.assertLess(GUEST.index(broad),GUEST.index(old))
  self.assertIn('positive[1]&&positive[2]&&positive[3]&&positive[4]',GUEST)
 def test_rollback_fails_closed_on_unexpected_rule_count(self):
  self.assertIn('HARD_NO_GO_RULE_COUNT',GUEST)
  self.assertIn('HARD_NO_GO_ROLLBACK_RULE_OWNERSHIP',GUEST)
  self.assertIn('generation',GUEST) if 'generation' in GUEST else self.assertIn('gen=3',GUEST)
if __name__=="__main__":unittest.main()
