"""RC36 strict Xray session inventory source/proxy log contract and mutants."""
import unittest
from pathlib import Path
from xray.lab.rc36_pinned_xray_udp_source_audit import BLOBS,SourceDrift,review
ROOT=Path(__file__).resolve().parents[1]
GUEST=(ROOT/"xray/lab/rc36_xray_internal_udp_expiry_guest.sh").read_text()
HOST=(ROOT/"xray/lab/rc36_xray_internal_udp_expiry_netns.sh").read_text()
RUN=(ROOT/"xray/lab/rc36_xray_internal_udp_expiry_runner.sh").read_text()
class RC36SessionProof(unittest.TestCase):
 def test_exact_real_log_dispatch_count_for_same_source(self):
  self.assertIn("processing connection from:",GUEST)
  self.assertIn('old_source_port=',GUEST)
  self.assertIn('if [ "$after_count" != 1 ]',GUEST)
  self.assertIn("XRAY_UDP_PROCESS_RECREATED_AFTER_CONNTRACK_EXPIRY",GUEST)
  self.assertIn("RC36_GUEST_XRAY_INTERNAL_PROCESS_ONCE_BEFORE_AFTER_CONNTRACK_EXPIRY",GUEST)
 def test_real_kernel_expiry_and_no_proxy_restart(self):
  self.assertIn("nf_conntrack_udp_timeout nf_conntrack_udp_timeout_stream",GUEST)
  self.assertIn("RC36_GUEST_KERNEL_OLD_UDP_CONNTRACK_EXPIRED_WHILE_BOTH_XRAY_PIDS_UNCHANGED",GUEST)
  self.assertIn('old_ticks',GUEST)
  self.assertIn('new_ticks',GUEST)
  self.assertIn("OLD_AFTER_EXPIRY_NO_CUTOVER",HOST)
 def test_disposable_no_fake_session_enumeration(self):
  self.assertIn("restrict=on",HOST)
  self.assertIn("unshare --net",RUN)
  self.assertIn("sha256sum -c -",RUN)
  self.assertIn("4.9.0-13-4kc-malta",RUN)
  self.assertIn("HARD_NO_GO_NO_COMPLETE_XRAY_UDP_OWNER_OR_ATOMIC_FREEZE",GUEST)
  self.assertNotIn("PRODUCTION_AUTHORIZED",GUEST+HOST+RUN)
 def test_pinned_source_shape_requires_five_files(self):
  self.assertEqual(len(BLOBS),5)
  self.assertIn("app/proxyman/inbound/worker.go",BLOBS)
  self.assertIn("app/router/command/command.proto",BLOBS)
 def test_fail_closed_on_source_drift(self):
  from xray.lab.rc36_pinned_xray_udp_source_audit import review
  # Tests must remain offline: a fake missing worker session field cannot
  # satisfy the source authority gate.
  fake={path:"service Test { rpc Something (A) returns (B) {} }" for path in BLOBS}
  with self.assertRaisesRegex(SourceDrift,"MISSING_INTERNAL_SESSION_WITNESS"):review(fake)
 def test_gate_rejects_new_unreviewed_session_api(self):
  fake={path:"" for path in BLOBS}
  worker="""type connID struct {src net.Destination;dest net.Destination}
   activeConn map[connID]*udpConn
   if !w.cone {
   nowSec-atomic.LoadInt64(&conn.lastActivityTime) > 2*60
   conn, found := w.activeConn[id]
   w.activeConn[id] = conn
   func (w *udpWorker) removeConn(id connID)
  """
  fake["app/proxyman/inbound/worker.go"]=worker
  fake["proxy/dokodemo/dokodemo.go"]="processing connection from:"
  for path in ("app/proxyman/command/command.proto","app/stats/command/command.proto",
               "app/router/command/command.proto"):
   fake[path]="service Test {rpc ListUdpSession (A) returns (B) {}}"
  with self.assertRaisesRegex(SourceDrift,"POSSIBLE_NEW_OWNER_API"):review(fake)
if __name__=="__main__":unittest.main()
