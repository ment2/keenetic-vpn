"""Pure cgroup v1 kernel49 contract adversarial tests."""
import dataclasses
import unittest
from xray.lab.v30_kernel49_cgroup_v1_contract import inspect,parse_proc_cgroups,parse_mounts
from xray.lab.v30_sealed_descendant_inventory import Snapshot

GROUPS="#subsys_name hierarchy num_cgroups enabled\npids 7 5 1\ncpu 2 7 1\n"
MOUNTS="42 1 0:32 / /sys/fs/cgroup/pids rw,relatime - cgroup cgroup rw,pids\n"
def snap(g):
    return Snapshot(g,"/v30",(),(),membership_enumeration_complete=True,
        listener_enumeration_complete=True,scope_was_sealed_before_any_spawn=True,
        all_writers_in_same_scope=True,scope_kernel49_available=True)
READY=dict(scope="/v30",first=snap(1),second=snap(2),
           boot_guardian_outside_usb=True,scope_created_before_spawn=True,
           escape_impossible=True,legacy_spawners_fenced=True,all_proc_files_readable=True)

class Kernel49CgroupV1Tests(unittest.TestCase):
    def test_synthetic_positive_still_never_proves_physical(self):
        r=inspect(GROUPS,MOUNTS,**READY)
        self.assertEqual(r["status"],"OFFLINE_LOGICAL_CONTRACT_ONLY")
        self.assertFalse(r["real_kernel49_cgroup_support_proven"])
        self.assertFalse(r["physical_descendant_containment_proven"])
        self.assertFalse(r["production_recovery_authorized"])
        self.assertEqual(r["router_commands"],[])
    def test_missing_pids_controller(self):
        r=inspect(GROUPS.replace("pids 7 5 1","pids 7 5 0"),MOUNTS,**READY)
        self.assertIn("CGROUP_V1_PIDS_CONTROLLER_NOT_PROVEN",r["reason_codes"])
    def test_not_mounted(self):
        r=inspect(GROUPS,"42 1 0:32 / /sys/fs/cgroup/pids rw - tmpfs none rw\n",**READY)
        self.assertIn("NO_UNIQUE_WRITABLE_PIDS_CGROUP_V1_MOUNT",r["reason_codes"])
    def test_mount_read_only(self):
        r=inspect(GROUPS,MOUNTS.replace("rw,relatime","ro,relatime"),**READY)
        self.assertIn("NO_UNIQUE_WRITABLE_PIDS_CGROUP_V1_MOUNT",r["reason_codes"])
    def test_second_pids_mount_ambiguous(self):
        r=inspect(GROUPS,MOUNTS+MOUNTS.replace("42 1","44 1"),**READY)
        self.assertIn("NO_UNIQUE_WRITABLE_PIDS_CGROUP_V1_MOUNT",r["reason_codes"])
    def test_incomplete_other_evidence(self):
        for name in ("boot_guardian_outside_usb","scope_created_before_spawn",
                     "escape_impossible","legacy_spawners_fenced","all_proc_files_readable"):
            with self.subTest(name=name):
                r=inspect(GROUPS,MOUNTS,**{**READY,name:False})
                self.assertEqual(r["status"],"NO_PRODUCTION_RECOVERY")
    def test_read_only_cgroup_data_never_validates_runtime(self):
        r=inspect("not valid","not valid",**READY)
        self.assertIn("UNTRUSTED_KERNEL_CGROUP_DATA",r["reason_codes"])
    def test_group_not_matching_snapshot_blocks(self):
        r=inspect(GROUPS,MOUNTS,**{**READY,"scope":"/other"})
        self.assertIn("SCOPE_NOT_BOUND_TO_SNAPSHOT",r["reason_codes"])
    def test_nonconsecutive_scans_block(self):
        r=inspect(GROUPS,MOUNTS,**{**READY,"second":snap(3)})
        self.assertIn("NONCONSECUTIVE_SNAPSHOT_GENERATIONS",r["reason_codes"])
    def test_missing_second_scan_blocks(self):
        r=inspect(GROUPS,MOUNTS,**{**READY,"second":None})
        self.assertIn("MISSING_TWO_MEMBER_SNAPSHOTS",r["reason_codes"])
    def test_duplicate_controller_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_proc_cgroups(GROUPS+"pids 7 6 1\n")

if __name__=="__main__":unittest.main()
