"""RC34 real Linux4.9 kernel conntrack source and old SILENT UDP negative/positive control."""
from pathlib import Path
import unittest
R=Path(__file__).resolve().parents[1]
G=(R/"xray/lab/rc34_conntrack_idle_first_tproxy_guest.sh").read_text()
H=(R/"xray/lab/rc34_conntrack_idle_first_tproxy_netns.sh").read_text()
RUN=(R/"xray/lab/rc34_conntrack_idle_first_tproxy_runner.sh").read_text()
MOD=(R/"xray/lab/rc34_conntrack_module_pack.py").read_text()
class RC34Conntrack(unittest.TestCase):
 def test_archived_kernel_modules_disposable_only(self):
  self.assertIn('"nf_conntrack","nf_conntrack_ipv4"',MOD)
  self.assertIn("rc34_conntrack_module_pack",RUN)
  self.assertIn("4.9.0-13-4kc-malta",RUN)
  self.assertIn("sha256sum -c -",RUN)
  self.assertIn("unshare --net",RUN)
  self.assertIn("restrict=on",H)
 def test_silent_was_actually_active_before_observer(self):
  self.assertLess(H.index("OLD_IDLE_PRIMED"),H.index("RC34_GUEST_OLD_AND_API_ENABLED"))
  self.assertIn("OLD_IDLE_RESUMED_DURING",H)
  self.assertIn("SILENT_PREEXISTING_UDP_SOURCE_PORT",H)
  self.assertLess(G.index("RC34_GUEST_IDLE_UDP_PRIME_READY"),G.index("/lab/rc34-observer 2 eth1"))
 def test_independent_kernel_source_must_exist(self):
  self.assertIn("/proc/net/nf_conntrack",G)
  self.assertIn("HARD_NO_GO_KERNEL_CONNTRACK_PROCFS_UNAVAILABLE",G)
  self.assertIn("HARD_NO_GO_KERNEL_CONNTRACK_INVENTORY_INCOMPLETE",G)
  self.assertIn("kernel_count",G)
  self.assertIn("AF_PACKET_NOT_IN_KERNEL_MAP",G)
 def test_readback_and_old_owner_counters(self):
  for token in ("flow_count=0","flow_count=$((flow_count+1))",
                "positive[6]","expected_rules","HARD_NO_GO_BOTH_TPROXY_OWNERS_NOT_WITNESSED",
                "STALE_CAS_ROLLBACK","/proc/sys/kernel/random/boot_id"):
   self.assertIn(token,G)
 def test_no_false_generic_authorization(self):
  self.assertIn("HARD_NO_GO_DYNAMIC_UDP_5TUPLE_CAS_PRIVILEGED_LEGACY_FENCING_PHYSICAL",H)
  self.assertNotIn("PRODUCTION_AUTHORIZED",RUN+G+H)
  self.assertIn("RC34_HOST: PASS_THREE_OLD_UDP_INCLUDING_PREVIOUSLY_IDLE",H)
if __name__=="__main__":unittest.main()
