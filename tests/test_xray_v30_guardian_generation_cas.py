"""Two competing guardian generations CAS test; no live PID signals."""
import concurrent.futures
from pathlib import Path
import tempfile
import unittest
from xray.staging.v30_kernel49_cooperative_ledger import Ledger
from xray.staging.v30_supervisor_core import FenceError

PROOF={x:True for x in (
    "old_parent_exited","old_child_exited","all_descendants_drained",
    "old_listener_absent","rescue_sha_verified","no_unfenced_writers",
    "two_consecutive_sealed_scope_scans")}

class GuardianGenerationTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.ledger=Ledger(Path(t.name))
        self.owner=self.ledger.open_owner(fresh_known_absence=True)
    def test_concurrent_guardians_only_one_claims_generation(self):
        def claim(_):
            try:return self.ledger.begin_scoped_recovery(
                expected_generation=self.owner["generation"],guardian_ticks=111)
            except FenceError:return None
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            results=list(pool.map(claim,range(12)))
        allowed=[v for v in results if v is not None]
        self.assertEqual(len(allowed),1)
        self.assertTrue(self.ledger.read()["blocked"])
        self.assertEqual(self.ledger.read()["recovery_claim"],allowed[0])
    def test_second_takeover_is_cas_limited(self):
        first=self.ledger.begin_scoped_recovery(expected_generation=
                    self.owner["generation"],guardian_ticks=111)
        with self.assertRaises(FenceError):
            self.ledger.takeover_scoped_recovery(first,guardian_ticks=222)
        next_claim=self.ledger.takeover_scoped_recovery(
            first,guardian_ticks=222,verified_old_guardian_dead=True)
        self.assertEqual(next_claim["attempt"],2)
        self.assertNotEqual(next_claim["token"],first["token"])
        with self.assertRaises(FenceError):
            self.ledger.takeover_scoped_recovery(
                first,guardian_ticks=333,verified_old_guardian_dead=True)
        with self.assertRaises(FenceError):
            self.ledger.finish_scoped_recovery(first,PROOF)
        r=self.ledger.finish_scoped_recovery(next_claim,PROOF)
        self.assertEqual(r["status"],"LAB_SCOPED_RECOVERY_ONLY")
        self.assertFalse(r["production_authorized"])
        fresh=self.ledger.open_owner(fresh_known_absence=True)
        self.assertEqual(fresh["generation"],self.owner["generation"]+1)
        with self.assertRaises(FenceError):
            self.ledger.begin_scoped_recovery(expected_generation=
                self.owner["generation"],guardian_ticks=44)
    def test_no_legacy_reconcile_bypass_claimed_guardian(self):
        claim=self.ledger.begin_scoped_recovery(expected_generation=
                    self.owner["generation"],guardian_ticks=111)
        with self.assertRaisesRegex(FenceError,"already claimed"):
            self.ledger.reconcile_for_lab(PROOF)
        self.assertEqual(self.ledger.read()["recovery_claim"],claim)
    def test_new_requests_denied_when_guardian_claims(self):
        claim=self.ledger.begin_scoped_recovery(expected_generation=
                    self.owner["generation"],guardian_ticks=111)
        with self.assertRaises(FenceError):
            self.ledger.submit("S97","RESTART")
        with self.assertRaises(FenceError):
            self.ledger.close_owner(self.owner,proved_child_absent=True)
    def test_inflight_uncertain_recorded_only_once_across_guardian_failover(self):
        req=self.ledger.submit("S97","RESTART")
        self.ledger.submit("cron","CHECK_HEALTH")
        self.ledger.claim(self.owner)
        first=self.ledger.begin_scoped_recovery(expected_generation=
                    self.owner["generation"],guardian_ticks=1)
        self.assertEqual(len([r for r in self.ledger.read()["receipts"]
                             if r["sequence"]==req["sequence"]]),1)
        next_claim=self.ledger.takeover_scoped_recovery(first,
                        guardian_ticks=2,verified_old_guardian_dead=True)
        self.ledger.finish_scoped_recovery(next_claim,PROOF)
        rows=self.ledger.read()["receipts"]
        self.assertEqual([r["status"] for r in rows],
                         ["UNCERTAIN","CANCELLED_UNCERTAIN"])
        self.assertFalse(self.ledger.read()["pending"])
    def test_partial_evidence_never_commits(self):
        claim=self.ledger.begin_scoped_recovery(expected_generation=
                    self.owner["generation"],guardian_ticks=111)
        for missing in PROOF:
            with self.subTest(field=missing):
                partial={**PROOF,missing:False}
                with self.assertRaises(FenceError):
                    self.ledger.finish_scoped_recovery(claim,partial)
                self.assertIsNotNone(self.ledger.read()["recovery_claim"])
    def test_no_fabricated_host_approval(self):
        claim=self.ledger.begin_scoped_recovery(expected_generation=
                    self.owner["generation"],guardian_ticks=111)
        self.assertFalse(self.ledger.finish_scoped_recovery(claim,PROOF)["production_authorized"])

if __name__=="__main__":unittest.main()
