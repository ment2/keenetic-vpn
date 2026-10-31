"""No-router staging shared-flock ledger: owner fences clients, never signals."""
import concurrent.futures
from pathlib import Path
import tempfile
import unittest

from xray.staging.v30_kernel49_cooperative_ledger import ACTORS, Ledger
from xray.staging.v30_supervisor_core import FenceError


class CooperativeLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.l=Ledger(self.root)

    def test_every_actor_has_exact_rights(self):
        self.assertEqual(set(ACTORS),{"S97","S98","S99","watchdog","cron","guardian"})
        self.assertEqual(ACTORS["S97"],{"START","STOP","RESTART"})
        self.assertEqual(ACTORS["S98"],{"CHECK_TPROXY"})
        for role in ("S99","watchdog","cron"):
            self.assertEqual(ACTORS[role],{"CHECK_HEALTH"})
        for actor,action in (("cron","RESTART"),("watchdog","STOP"),
                             ("S98","RESTART"),("S97","CHECK_TPROXY"),
                             ("guardian","RECOVER"),("S97","killall")):
            with self.subTest(actor=actor,action=action):
                with self.assertRaises(FenceError):
                    self.l.submit(actor,action)

    def test_concurrent_unique_sequence_with_one_flock(self):
        items=[("S97","START"),("S97","RESTART"),("watchdog","CHECK_HEALTH"),
               ("cron","CHECK_HEALTH"),("S98","CHECK_TPROXY")]*3
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            results=list(pool.map(lambda it:self.l.submit(*it),items))
        self.assertEqual(set(x["sequence"] for x in results),set(range(1,16)))
        self.assertEqual(len(self.l.read()["pending"]),15)
        self.assertEqual(self.l.lock.stat().st_mode & 0o777,0o600)
        self.assertEqual(self.l.state.stat().st_mode & 0o777,0o600)

    def test_queue_is_bounded(self):
        for _ in range(24):self.l.submit("S99","CHECK_HEALTH")
        with self.assertRaisesRegex(FenceError,"bounded queue"):
            self.l.submit("S97","START")

    def test_exact_generation_owns_only_one_inflight(self):
        x=self.l.submit("S97","START")
        owner=self.l.open_owner(fresh_known_absence=True)
        self.assertEqual(self.l.claim(owner),x)
        with self.assertRaises(FenceError):self.l.claim(owner)
        with self.assertRaises(FenceError):
            self.l.complete({**owner,"generation":999},x,"DONE")
        self.l.complete(owner,x,"DONE")
        self.assertEqual(self.l.read()["receipts"][0]["status"],"DONE")
        self.l.close_owner(owner,proved_child_absent=True)
        self.assertIsNone(self.l.read()["owner"])

    def test_stale_parent_requires_uncertain_manual_reconciliation(self):
        req=self.l.submit("S97","RESTART")
        self.l.submit("cron","CHECK_HEALTH")
        owner=self.l.open_owner(fresh_known_absence=True)
        self.l.claim(owner)
        with self.assertRaisesRegex(FenceError,"UNCERTAIN"):
            self.l.open_owner(fresh_known_absence=True)
        saved=self.l.read()
        self.assertTrue(saved["blocked"])
        self.assertEqual(saved["receipts"][0]["status"],"UNCERTAIN")
        with self.assertRaises(FenceError):self.l.submit("S97","START")
        with self.assertRaises(FenceError):self.l.claim(owner)
        with self.assertRaises(FenceError):self.l.reconcile_for_lab({"old_child_exited":True})
        proof={x:True for x in ("old_parent_exited","old_child_exited",
                               "all_descendants_drained","old_listener_absent",
                               "rescue_sha_verified","no_unfenced_writers")}
        report=self.l.reconcile_for_lab(proof)
        self.assertEqual(report["status"],"OFFLINE_RECONCILED_ONLY")
        receipts=self.l.read()["receipts"]
        self.assertEqual({r["status"] for r in receipts},
                         {"UNCERTAIN","CANCELLED_UNCERTAIN"})
        self.assertFalse(self.l.read()["production_authorized"])
        self.assertEqual(self.l.read()["pending"],[])
        new=self.l.open_owner(fresh_known_absence=True)
        self.assertNotEqual(new["generation"],owner["generation"])

    def test_guardian_quarantine_never_replays(self):
        self.l.submit("S97","RESTART")
        old=self.l.open_owner(fresh_known_absence=True)
        self.l.claim(old)
        self.assertTrue(self.l.quarantine_stale())
        self.assertEqual(self.l.read()["receipts"][0]["status"],"UNCERTAIN")
        self.assertFalse(self.l.quarantine_stale())
        with self.assertRaises(FenceError):self.l.close_owner(old,proved_child_absent=True)

    def test_unknown_old_child_blocks_owner(self):
        with self.assertRaisesRegex(FenceError,"unknown old process"):
            self.l.open_owner(fresh_known_absence=False)
        self.assertIsNone(self.l.read()["owner"])

    def test_receipt_must_not_invent_success(self):
        x=self.l.submit("S97","START")
        owner=self.l.open_owner(fresh_known_absence=True)
        self.l.claim(owner)
        with self.assertRaises(FenceError):self.l.complete(owner,x,"UNCERTAIN")

    def test_root_outside_disposable_denied(self):
        with self.assertRaises(FenceError):Ledger("/opt/etc/xray")

    def test_production_flag_cannot_be_enabled(self):
        from xray.staging.v30_supervisor_core import atomic_journal
        x=self.l.read()
        x["production_authorized"]=True
        atomic_journal(self.l.state,x)
        with self.assertRaises(FenceError):self.l.submit("S97","START")


if __name__=="__main__":
    unittest.main()
