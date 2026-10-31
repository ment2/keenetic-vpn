"""Adversarial double-scan sealed-scope constraints: no false hardware proof."""
import dataclasses
import unittest
from xray.lab.v30_sealed_descendant_inventory import (
    Member,Snapshot,InventoryError,evaluate,
)
def clear(generation=1):
    return Snapshot(generation,"disposable-cgroup-v1",(),(),
        membership_enumeration_complete=True,
        listener_enumeration_complete=True,
        scope_was_sealed_before_any_spawn=True,
        all_writers_in_same_scope=True,
        scope_kernel49_available=True)
class SealedScopeTests(unittest.TestCase):
    def test_empty_fully_sealed_simulation_not_production(self):
        r=evaluate(clear(),clear(2))
        self.assertEqual(r["status"],"SYNTHETIC_DRAIN_CONTRACT_ONLY")
        self.assertFalse(r["production_recovery_authorized"])
        self.assertFalse(r["independent_physical_inventory_proven"])
        self.assertEqual(r["router_commands"],[])
    def test_unknown_kernel_scope_blocks_even_double_empty(self):
        for flag in ("scope_kernel49_available","scope_was_sealed_before_any_spawn",
                     "all_writers_in_same_scope","membership_enumeration_complete",
                     "listener_enumeration_complete"):
            with self.subTest(flag=flag):
                a=dataclasses.replace(clear(),**{flag:False})
                b=dataclasses.replace(clear(2),**{flag:False})
                self.assertEqual(evaluate(a,b)["status"],"NO_RESTART")
    def test_detached_unrecognizable_grandchild_still_blocks(self):
        orphan=Member(45454,777,1,"/bin/sleep",("sleep","forever"),(),"disposable-cgroup-v1")
        a=dataclasses.replace(clear(),members=(orphan,))
        b=dataclasses.replace(clear(2),members=(orphan,))
        self.assertIn("LIVE_SCOPE_MEMBER_OR_ORPHAN",evaluate(a,b)["reason_codes"])
    def test_reparent_drift_blocks_across_two_scans(self):
        a=dataclasses.replace(clear(),members=(Member(4,5,800,"/bin/sh",("sh",),(),"disposable-cgroup-v1"),))
        b=dataclasses.replace(clear(2),members=(Member(4,5,1,"/bin/sh",("sh",),(),"disposable-cgroup-v1"),))
        self.assertIn("DOUBLE_SCAN_IDENTITY_DRIFT",evaluate(a,b)["reason_codes"])
    def test_reused_pid_blocks_even_no_listener(self):
        a=dataclasses.replace(clear(),members=(Member(3,11,1,"/bin/x",("x",),(),"disposable-cgroup-v1"),))
        b=dataclasses.replace(clear(2),members=(Member(3,12,1,"/bin/y",("y",),(),"disposable-cgroup-v1"),))
        reasons=evaluate(a,b,direct_child=(3,11))["reason_codes"]
        self.assertIn("DIRECT_CHILD_PID_REUSE",reasons)
    def test_live_socket_without_fd_owner_blocks(self):
        a=dataclasses.replace(clear(),open_socket_inodes=(1234,))
        b=dataclasses.replace(clear(2),open_socket_inodes=(1234,))
        self.assertIn("UNATTRIBUTED_TCP_UDP_SOCKET",evaluate(a,b)["reason_codes"])
    def test_unknown_proc_permission_blocks(self):
        a=dataclasses.replace(clear(),unreadable_pids=(777,))
        b=dataclasses.replace(clear(2),unreadable_pids=(777,))
        self.assertIn("UNREADABLE_PROC_FD_OR_NET",evaluate(a,b)["reason_codes"])
    def test_process_can_rename_argv_but_still_in_scope(self):
        p=Member(88,99,1,"/usr/bin/renamed",("not-xray",),(),"disposable-cgroup-v1")
        a=dataclasses.replace(clear(),members=(p,))
        b=dataclasses.replace(clear(2),members=(p,))
        self.assertEqual(evaluate(a,b)["status"],"NO_RESTART")
    def test_process_escaped_scope_blocks(self):
        p=Member(55,88,1,"/bin/sleep",("sleep",),(),"elsewhere")
        a=dataclasses.replace(clear(),members=(p,))
        b=dataclasses.replace(clear(2),members=(p,))
        self.assertIn("PROCESS_ESCAPED_SEALED_SCOPE",evaluate(a,b)["reason_codes"])
    def test_scope_changed_between_snapshots_blocks(self):
        b=dataclasses.replace(clear(2),scope_id="other")
        self.assertIn("SCOPE_CHANGED_OR_UNKNOWN",evaluate(clear(),b)["reason_codes"])
    def test_snapshot_missing_generation_blocks(self):
        self.assertIn("NONCONSECUTIVE_SNAPSHOT_GENERATIONS",
                      evaluate(clear(),clear(3))["reason_codes"])
    def test_duplicates_block(self):
        p=Member(88,99,1,"/bin/x",("x",),(),"disposable-cgroup-v1")
        a=dataclasses.replace(clear(),members=(p,p))
        b=dataclasses.replace(clear(2),members=(p,p))
        self.assertIn("BAD_OR_REUSED_PID_IDENTITY",evaluate(a,b)["reason_codes"])
    def test_no_live_proc_reader_does_not_override_hardware(self):
        from xray.lab import v30_sealed_descendant_inventory as m
        import inspect
        source=inspect.getsource(m)
        self.assertNotIn("os.kill(",source)
        self.assertNotIn("subprocess.run(",source)
        self.assertNotIn("Path('/proc')",source)
if __name__=="__main__":unittest.main()
