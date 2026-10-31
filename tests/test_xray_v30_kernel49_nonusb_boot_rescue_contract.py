"""Independent non-USB boot guardian planning and chaos gates, no router I/O."""
import dataclasses
import unittest
from xray.lab.v30_kernel49_nonusb_boot_rescue_contract import (
    Evidence,Fault,RescueBlocked,LAYOUT,acceptance,
)
class BootRescueTests(unittest.TestCase):
    def test_default_refuses_every_hardware_claim(self):
        r=acceptance()
        self.assertEqual(r["decision"],"HARD_NO_GO")
        self.assertFalse(r["physical_boot_proven"])
        self.assertFalse(r["automatic_restore_authorized"])
        self.assertEqual(r["production_commands"],[])
        self.assertGreaterEqual(len(r["reasons"]),15)
    def test_individual_unverified_property_refuses(self):
        yes=Evidence(**{f.name:True for f in dataclasses.fields(Evidence)})
        for f in dataclasses.fields(Evidence):
            with self.subTest(field=f.name):
                bad=dataclasses.replace(yes,**{f.name:False})
                reasons=acceptance(bad)["reasons"]
                self.assertIn("MISSING_"+f.name.upper(),reasons)
    def test_all_synthetic_pass_remains_not_authorized(self):
        yes=Evidence(**{f.name:True for f in dataclasses.fields(Evidence)})
        r=acceptance(yes)
        self.assertEqual(r["decision"],"SYNTHETIC_CONTRACT_SATISFIED_ONLY")
        self.assertFalse(r["physical_boot_proven"])
        self.assertFalse(r["automatic_restore_authorized"])
    def test_each_failure_injection_fails_even_full_synthetic_proof(self):
        yes=Evidence(**{f.name:True for f in dataclasses.fields(Evidence)})
        for f in dataclasses.fields(Fault):
            with self.subTest(case=f.name):
                fail=dataclasses.replace(Fault(),**{f.name:True})
                r=acceptance(yes,fail)
                # Missing USB alone is acceptable only if a separate
                # guardian/backup are already independently available.
                if f.name=="missing_usb":
                    self.assertFalse(r["automatic_restore_authorized"])
                else:
                    self.assertEqual(r["decision"],"HARD_NO_GO")
    def test_corrupt_backup_cannot_trigger_restore(self):
        yes=Evidence(**{f.name:True for f in dataclasses.fields(Evidence)})
        r=acceptance(yes,Fault(missing_usb=True,archive_corrupt=True))
        self.assertIn("BAD_RESCUE_SHA",r["reasons"])
        self.assertFalse(r["automatic_restore_authorized"])
    def test_power_loss_before_fsync_and_mid_restore_denied(self):
        yes=Evidence(**{f.name:True for f in dataclasses.fields(Evidence)})
        for f in (Fault(power_loss_before_journal_fsync=True),
                  Fault(power_loss_during_script_restore=True)):
            self.assertIn("CORRUPT_OR_UNFSYNCED_JOURNAL",
                          acceptance(yes,f)["reasons"])
    def test_device_alias_and_live_orphan_denied(self):
        yes=Evidence(**{f.name:True for f in dataclasses.fields(Evidence)})
        r=acceptance(yes,Fault(rescue_same_device=True,old_descendant_alive=True))
        self.assertIn("SAME_USB_MOUNT",r["reasons"])
        self.assertIn("FOREIGN_DESCENDANT_LIVE",r["reasons"])
    def test_no_programmable_live_mode(self):
        with self.assertRaises(RescueBlocked):
            acceptance(offline=False)
    def test_boot_layout_no_real_path_provision(self):
        self.assertEqual(len(LAYOUT),6)
        self.assertTrue(all(x.startswith("rescue-v30/") for x in LAYOUT.values()))
        self.assertFalse(any(x.startswith("/opt") for x in LAYOUT.values()))
if __name__=="__main__":unittest.main()
