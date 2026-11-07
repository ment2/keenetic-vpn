"""RC41 strict source-grounded Go instrumented in-process worker contracts.

A green source contract or test-only Go worker is not live legacy inventory,
kernel-owner freezing, physical root fencing or rescue approval.
"""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
GO=(ROOT/"xray/lab/rc41_pinned_xray_worker_instrumented_test.go").read_text()
RUN=(ROOT/"xray/lab/rc41_pinned_worker_source_runner.sh").read_text()
YML=(ROOT/".github/workflows/xray-v30-rc41-private-udp-owner.yml").read_text()
class RC41(unittest.TestCase):
 def test_instrumentation_is_test_only_pinned_source(self):
  self.assertTrue(GO.startswith("// RC41 DISPOSABLE TEST-ONLY"))
  self.assertIn("package inbound",GO)
  self.assertIn("func rc41Snapshot(w *udpWorker)",GO)
  self.assertIn("w.RLock()",GO)
  self.assertIn("w.RUnlock()",GO)
  self.assertIn('activeConn:make(map[connID]*udpConn)',GO)
  self.assertIn("app/proxyman/inbound/worker.go",RUN)
  self.assertIn("ef454d21195e2df878cd129f907dfaa65f7cdff0",RUN)
  self.assertIn("12ee51e4bb1d02ece4ef4b7114efa2bcdc130995",RUN)
  self.assertIn("git hash-object",RUN)
  self.assertIn("rc41_pinned_xray_worker_instrumented_test.go",RUN)
 def test_real_udp_hub_socket_cookie_and_private_dispatch(self):
  for marker in ["w.Start()","rc41Echo(t,a,host","rc41Echo(t,b,host",
                 "unix.GetsockoptUint64","unix.SO_COOKIE","srcA.Port","srcB.Port",
                 "echo.started.Load()!=2","w.hub.udpConn"]:
   self.assertIn(marker,GO)
  self.assertIn("RC41_REAL_LINUX_UDP_SOCKET_COOKIES_AND_HUB_OWNER_WITNESSED",GO)
 def test_unfrozen_snapshot_is_rejected(self):
  for marker in ["frozenView:=rc41Snapshot(w)","B_NEW_AFTER_SNAPSHOT",
                 "RC41_PRIVATE_SNAPSHOT_RWLOCK_IS_NOT_KERNEL_INGRESS_FREEZE",
                 "RC41_HARD_NO_GO_PRODUCTION_NO_ATOMIC_OWNER_COMMIT_OR_PHYSICAL_FENCING"]:
   self.assertIn(marker,GO)
  self.assertNotIn("PRODUCTION_AUTHORIZED",GO)
 def test_cleanup_uses_real_worker_120_seconds(self):
  self.assertIn("w.clean()",GO)
  self.assertIn("time.Now().Unix()-121",GO)
  self.assertIn("RC41_PRIVATE_XRAY_WORKER_120S_CLEANER_TEST_ONLY",GO)
 def test_disposable_network_only(self):
  self.assertIn("unshare --net",RUN)
  self.assertIn("ip link set lo up",RUN)
  self.assertIn("ip -4 route show default",RUN)
  self.assertIn("GITHUB_ACTIONS",RUN)
  self.assertIn("setpriv --reuid=65534 --regid=65534 --clear-groups",RUN)
 def test_no_release_or_router_mutations(self):
  for bad in ["killall","ssh root@","curl -k","StrictHostKeyChecking=no",
              "iptables -t mangle -A PREROUTING","kubectl"]:
   self.assertNotIn(bad,RUN+GO)
  self.assertIn("HARD_NO_GO_PRODUCTION",GO)
 def test_ci_owns_source_blob_and_has_bounded_go_run(self):
  self.assertIn("ubuntu-24.04",YML)
  self.assertIn("go-version: '1.25.7'",YML)
  self.assertIn("timeout-minutes: 18",YML)
  self.assertIn("timeout --signal=TERM 150s",RUN)
if __name__=="__main__": unittest.main()
