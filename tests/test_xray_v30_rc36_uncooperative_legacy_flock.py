"""RC36 disposable witness: cooperative flock cannot fence an uncooperative actor.

No router, no root, no real process, no privileged actions. This is a
counterexample to treating a controller's flock as mandatory root fencing.
"""
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from xray.lab.rc31_privileged_legacy_evidence_gate import SOURCES, PhysicalEvidence, evaluate

class RC36AdvisoryBypass(unittest.TestCase):
    def test_uncooperative_legacy_process_ignores_owner_flock(self):
        with tempfile.TemporaryDirectory(prefix="rc36-flock-only-negative-") as td:
            base=Path(td)
            lease=base/"owner.lock"
            trace=base/"sandbox-only-event.txt"
            with lease.open("a+") as locked:
                fcntl.flock(locked,fcntl.LOCK_EX|fcntl.LOCK_NB)
                code=(
                    "from pathlib import Path;import sys;"
                    "Path(sys.argv[1]).write_text('IGNORED_CONTROLLER_ADVISORY_LOCK')"
                )
                child=subprocess.run([sys.executable,"-c",code,str(trace)],
                    capture_output=True,text=True,timeout=5,check=True)
                self.assertEqual(child.returncode,0)
                self.assertEqual(trace.read_text(),"IGNORED_CONTROLLER_ADVISORY_LOCK")
                # Parent still owns the lock, yet independent action succeeded.
                with lease.open("a+") as other:
                    with self.assertRaises(BlockingIOError):
                        fcntl.flock(other,fcntl.LOCK_EX|fcntl.LOCK_NB)
                fcntl.flock(locked,fcntl.LOCK_UN)
    def test_all_seven_entrypoints_still_require_live_kernel_evidence(self):
        r=evaluate(expected_hashes=None,boot_id="",generation=0,
                   physical=PhysicalEvidence())
        self.assertEqual(set(SOURCES),{
            "S97xray","S98xray-wifi","S99xray-watchdog","xray-watchdog.sh",
            "xray-wifi-rules.sh","xray-fc-cron-guard.sh","xray-safe-hourly.sh"
        })
        self.assertEqual(r["decision"],"HARD_NO_GO_PRODUCTION")
        self.assertFalse(r["live_fencing_proven"])
        self.assertFalse(r["production_authorized"])
        self.assertEqual(r["router_actions"],())
        self.assertIn("ROOT_CGROUP_V1_ESCAPE_OBSERVED_RC11",r["reasons"])
    def test_complete_snapshot_does_not_equal_process_fence(self):
        from xray.lab.rc31_privileged_legacy_evidence_gate import snapshot_hashes
        r=evaluate(expected_hashes=snapshot_hashes(),boot_id="00000000-1111-2222-3333-444444444444",
                   generation=1,physical=PhysicalEvidence())
        self.assertEqual(r["snapshot_count"],7)
        self.assertFalse(r["live_fencing_proven"])
        self.assertFalse(r["production_authorized"])
if __name__=="__main__":
    unittest.main()
