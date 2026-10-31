"""Offline-only two-phase v30 migration review gates and failure cases."""
import dataclasses
import inspect
import unittest
from xray.lab import v30_two_phase_migration_contract as m


class TwoPhaseMigrationTests(unittest.TestCase):
    def test_default_no_go_and_no_commands(self):
        r=m.phase_plan()
        self.assertEqual(r["decision"], "REVIEW_ONLY_NO_PRODUCTION_CHANGE")
        self.assertFalse(r["deployment_authorized"])
        self.assertFalse(r["trial_authorized"])
        self.assertEqual(r["production_commands"], [])
        self.assertEqual(r["manifest_verified"], 9)
        self.assertIn("NO_FRESH_LIVE_PROCESS_SNAPSHOT",r["reasons"])

    def test_legacy_entrypoints_including_cron(self):
        self.assertTrue({"S97xray","S98xray-wifi","S99xray-watchdog",
                         "xray-watchdog.sh","xray-wifi-rules.sh",
                         "xray-fc-cron-guard.sh","xray-safe-hourly.sh"}.issubset(
                             set(m.LEGACY_ACTORS)))

    def test_release_requires_every_independent_evidence(self):
        all_yes=m.GateEvidence(**{f.name:True for f in dataclasses.fields(m.GateEvidence)})
        clean=m.Snapshot(generation=1,roots=(),children=(),orphan_writers=(),
                         cron_unknown=False,boot_unknown=False)
        self.assertEqual(m.phase_plan(all_yes,clean)["reasons"],[])
        self.assertFalse(m.phase_plan(all_yes,clean)["deployment_authorized"])
        for f in dataclasses.fields(m.GateEvidence):
            with self.subTest(field=f.name):
                e=dataclasses.replace(all_yes,**{f.name:False})
                self.assertIn("NO_"+f.name.upper(),m.phase_plan(e,clean)["reasons"])

    def test_quiesced_parent_still_has_active_descendant(self):
        snapshot=m.Snapshot(1,(),((222,99,1000),),(),False,False)
        problems=m.inspect_snapshot(snapshot)
        self.assertIn("UNFENCED_LEGACY_DESCENDANT",problems)

    def test_orphan_writer_from_old_wifi_rules_blocks(self):
        snapshot=m.Snapshot(1,(),(),((333,1020),),False,False)
        self.assertIn("ORPHANED_LEGACY_WRITER",m.inspect_snapshot(snapshot))

    def test_old_watchdog_or_s98_running_blocks(self):
        snapshot=m.Snapshot(1,((32713,61575997),(24097,60711544)),(),(),False,False)
        self.assertIn("LEGACY_ROOT_STILL_PRESENT",m.inspect_snapshot(snapshot))

    def test_bad_and_duplicate_identity_refused(self):
        cases=(
            m.Snapshot(0,(),(),(),False,False),
            m.Snapshot(1,((44,0),),(),(),False,False),
            m.Snapshot(1,((44,1),(44,2)),(),(),False,False),
            m.Snapshot(1,((44,1),),((44,1,3),),(),False,False),
            m.Snapshot(1,((44,1),),(),((44,3),),False,False),
        )
        for obj in cases:
            with self.subTest(snapshot=obj):
                self.assertTrue(m.inspect_snapshot(obj))

    def test_cron_or_boot_not_fully_scanned_blocks(self):
        a=m.Snapshot(1,(),(),(),True,False)
        b=m.Snapshot(1,(),(),(),False,True)
        self.assertIn("CRON_SPAWNER_INVENTORY_UNKNOWN",m.inspect_snapshot(a))
        self.assertIn("BOOT_SPAWNER_INVENTORY_UNKNOWN",m.inspect_snapshot(b))

    def test_phase_order_has_no_skip_or_rollback_in_band(self):
        yes=m.GateEvidence(**{f.name:True for f in dataclasses.fields(m.GateEvidence)})
        clean=m.Snapshot(1,(),(),(),False,False)
        for i in range(len(m.STAGES)-1):
            v=m.transition(m.STAGES[i],m.STAGES[i+1],evidence=yes,snapshot=clean)
            self.assertFalse(v["deployment_authorized"])
            self.assertEqual(v["production_commands"],[])
        with self.assertRaises(ValueError):
            m.transition("PREPARE","ACTIVATE",evidence=yes,snapshot=clean)
        with self.assertRaises(ValueError):
            m.transition("MONITOR","PREPARE",evidence=yes,snapshot=clean)

    def test_manual_evidence_blocker_prevents_transition(self):
        with self.assertRaisesRegex(ValueError,"unverified"):
            m.transition("PREPARE","FREEZE_EXTERNAL_SPAWNERS",
                         evidence=m.GateEvidence(),snapshot=None)

    def test_untrusted_recovery_never_sends_signal(self):
        source=inspect.getsource(m)
        for text in ("os.kill(", "subprocess.", "killall xray", "iptables -F"):
            self.assertNotIn(text,source)

    def test_rollback_hold_preserves_kill_switch(self):
        rollback=m.phase_plan()["rollback"]
        self.assertIn("NO_SIGNAL",rollback["on_identity_drift"])
        self.assertIn("NO_WRITE",rollback["on_backup_loss"])


if __name__=="__main__":
    unittest.main()
