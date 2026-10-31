"""No real router mounts; reject same-device and unsafe rescue false confidence."""
import unittest
from xray.lab.v30_outofusb_mount_gate import assess,parse_mountinfo

MOUNTS = """31 1 8:1 / / rw,relatime - ext4 /dev/root rw
32 31 8:2 / /opt rw,relatime - ext4 /dev/sda1 rw
33 31 8:3 / /mnt/keenetic-rescue rw,relatime - ext4 /dev/mmcblk0p1 rw
"""
YES = dict(observed_after_cold_boot=True, root_owned_0700=True,
           independent_restore_after_usb_loss=True,sha256_archive_verified=True,
           guardian_exec_without_usb=True)

class OutOfUsbMountGateTests(unittest.TestCase):
    def test_valid_synthetic_mount_evidence_never_authorizes_production(self):
        result=assess(MOUNTS,**YES)
        self.assertEqual(result["status"],"OFFLINE_MOUNT_EVIDENCE_ONLY")
        self.assertFalse(result["production_rescue_authorized"])
        self.assertFalse(result["physical_router_reboot_proven"])
        self.assertEqual(result["production_commands"],[])

    def test_same_device_rejected(self):
        modified=MOUNTS.replace("33 31 8:3","33 31 8:2")
        reasons=assess(modified,**YES)["reasons"]
        self.assertIn("SAME_KERNEL_DEVICE",reasons)

    def test_same_mount_directory_not_independent(self):
        result=assess(MOUNTS.replace(
            "33 31 8:3 / /mnt/keenetic-rescue rw,relatime - ext4 /dev/mmcblk0p1 rw",""),
            **YES)
        self.assertIn("RESCUE_NOT_EXPLICIT_MOUNT_ROOT",result["reasons"])

    def test_tmpfs_not_reboot_durable(self):
        modified=MOUNTS.replace("ext4 /dev/mmcblk0p1","tmpfs none")
        self.assertIn("RESCUE_NOT_PERSISTENT_FS",assess(modified,**YES)["reasons"])

    def test_missing_any_physical_proof_blocks(self):
        for key in YES:
            with self.subTest(key=key):
                kwargs=dict(YES)
                kwargs[key]=False
                self.assertIn("NO_"+key.upper(),assess(MOUNTS,**kwargs)["reasons"])

    def test_invalid_mounts_do_not_authorize(self):
        for invalid in ("", "invalid", MOUNTS+MOUNTS.splitlines()[0]+"\n"):
            with self.subTest(data=invalid[:10]):
                self.assertNotEqual(assess(invalid,**YES)["status"],
                                    "OFFLINE_MOUNT_EVIDENCE_ONLY")

    def test_no_hardware_assumption_as_success(self):
        result=assess(MOUNTS)
        self.assertIn("NO_OBSERVED_AFTER_COLD_BOOT",result["reasons"])
        self.assertIn("NO_GUARDIAN_EXEC_WITHOUT_USB",result["reasons"])

    def test_genuinely_different_source_required(self):
        modified=MOUNTS.replace("8:3 / /mnt/keenetic-rescue rw,relatime - ext4 /dev/mmcblk0p1",
                                "8:3 / /mnt/keenetic-rescue rw,relatime - ext4 /dev/sda1")
        self.assertIn("SAME_BLOCK_SOURCE",assess(modified,**YES)["reasons"])

if __name__=="__main__":
    unittest.main()
