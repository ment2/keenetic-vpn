"""RC11 physical rescue can never be inferred from VM files on one runner."""
from dataclasses import replace, fields
import unittest
from xray.lab.rc11_hardware_boot_rescue_gate import RescueEvidence,assess_rescue
MOUNTS=("100 1 8:1 / /opt rw,relatime - ext4 /dev/sda1 rw\n"
        "101 1 179:3 / /mnt/keenetic-rescue rw,relatime - ext4 /dev/mtdblock3 rw\n")
def fixture():
    return RescueEvidence(MOUNTS,True,True,True,True,True,True,True,
                          True,True,True,True,True,True,True,True)
class RescueGate(unittest.TestCase):
    def test_missing_all_is_hard_no_go(self):
        d=assess_rescue(RescueEvidence())
        self.assertEqual(d["state"],"HARD_NO_GO")
        self.assertFalse(d["deployment_authorized"])
        self.assertIn("MOUNTINFO_UNTRUSTWORTHY",d["reasons"])
    def test_separately_mounted_synthetic_evidence_review_only(self):
        d=assess_rescue(fixture())
        self.assertEqual(d["state"],"OFFLINE_REVIEW_CANDIDATE_ONLY")
        self.assertFalse(d["physical_router_certified"])
        self.assertFalse(d["deployment_authorized"])
        self.assertFalse(d["production_commands"])
    def test_each_required_hardware_witness_missing_is_hard_no_go(self):
        for f in fields(RescueEvidence):
            if f.name=="mountinfo":continue
            with self.subTest(field=f.name):
                d=assess_rescue(replace(fixture(),**{f.name:False}))
                self.assertEqual(d["state"],"HARD_NO_GO")
                self.assertFalse(d["deployment_authorized"])
    def test_same_disk_is_rejected_even_with_all_true(self):
        same=MOUNTS.replace("179:3","8:1").replace("/dev/mtdblock3","/dev/sda1")
        d=assess_rescue(replace(fixture(),mountinfo=same))
        self.assertIn("SAME_KERNEL_DEVICE",d["reasons"])
        self.assertIn("SAME_BLOCK_SOURCE",d["reasons"])
    def test_mountpoint_not_separate_persistent_device_rejected(self):
        d=assess_rescue(replace(fixture(),mountinfo=MOUNTS.replace(" - ext4 /dev/mtdblock3"," - tmpfs tmpfs")))
        self.assertEqual(d["state"],"HARD_NO_GO")
        self.assertIn("RESCUE_NOT_PERSISTENT_FS",d["reasons"])
    def test_virtual_qemu_no_actual_powerloss(self):
        e=replace(fixture(),independent_physical_power_domain_verified=False,
                  test_proven_on_actual_keenetic_ndm5=False,
                  persistence_observed_after_actual_cold_boot=False)
        d=assess_rescue(e)
        self.assertIn("POWER_DOMAIN_UNVERIFIED",d["reasons"])
        self.assertIn("VENDOR_NDM5_NOT_PHYSICALLY_TESTED",d["reasons"])
        self.assertFalse(d["deployment_authorized"])
if __name__=="__main__":unittest.main()
