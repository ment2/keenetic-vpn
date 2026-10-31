"""Synthetic mutations only: never claim that privileged legacy writers were fenced."""
import unittest
from dataclasses import replace
from xray.lab.rc22_privileged_lineage_gate import (
    ACTORS, Entry, Task, evaluate, synthetic_fixture
)
class RC22PrivilegedLegacyLineage(unittest.TestCase):
    def setUp(self):
        self.e=synthetic_fixture()
        self.task=Task(ACTORS[0],124,22,999,self.e.boot_id,9,"b"*64,self.e.scope,False,(431,))
    def denied(self,e,reason):
        r=evaluate(e)
        self.assertEqual(r["decision"],"HARD_NO_GO",r)
        self.assertIn(reason,r["reasons"])
        self.assertFalse(r["production_authorized"])
        self.assertFalse(r["hardware_accepted"])
        self.assertEqual(r["router_commands"],())
    def test_synthetic_all_green_is_review_only(self):
        r=evaluate(self.e)
        self.assertEqual(r["decision"],"OFFLINE_REVIEW_CANDIDATE_ONLY")
        self.assertFalse(r["production_authorized"])
    def test_all_seven_executable_fence_fields_fail_closed(self):
        for i,actor in enumerate(self.e.entries):
            for attr,val,reason in (
                ("preboot_fenced",False,"ENTRY_PRIVILEGED_FENCE_UNPROVEN:"+actor.name),
                ("kernel_enforced",False,"ENTRY_PRIVILEGED_FENCE_UNPROVEN:"+actor.name),
                ("watchdog_cron_fenced",False,"ENTRY_PRIVILEGED_FENCE_UNPROVEN:"+actor.name),
                ("generation",8,"ENTRY_GENERATION_CAS_STALE:"+actor.name),
                ("live_sha256","", "ENTRY_EXE_SHA256_UNKNOWN:"+actor.name)):
                with self.subTest(actor=actor.name,field=attr):
                    updated=list(self.e.entries)
                    updated[i]=replace(actor,**{attr:val})
                    self.denied(replace(self.e,entries=tuple(updated)),reason)
    def test_each_independent_kernel_and_generation_gate(self):
        for attr,reason in (
            ("kernel_root_escape_absent_proven","OBSERVED_ROOT_CGROUP_ESCAPE_NOT_INDEPENDENTLY_FENCED"),
            ("independent_preboot_watcher_fencing","INDEPENDENT_WATCHDOG_PREBOOT_GATE_MISSING"),
            ("generation_cas_durable_and_exact","GENERATION_CAS_DURABILITY_UNPROVEN"),
            ("socket_inode_scan_complete","SOCKET_INODE_INVENTORY_UNPROVEN")):
            with self.subTest(attr=attr):
                self.denied(replace(self.e,**{attr:False}),reason)
    def test_unknown_privileged_or_outofscope_descendant_rejected(self):
        for child,reason in (
            (replace(self.task,actor="unidentified-root-cron"),"BEFORE_UNKNOWN_LEGACY_DESCENDANT"),
            (replace(self.task,privileged=True),"BEFORE_PRIVILEGED_CHILD_NOT_FENCED"),
            (replace(self.task,cgroup="/sys/fs/cgroup/root"),"BEFORE_DESCENDANT_ESCAPED_CGROUP"),
            (replace(self.task,generation=8),"BEFORE_BOOT_OR_GENERATION_CAS_MISMATCH"),
            (replace(self.task,boot_id="other-boot"),"BEFORE_BOOT_OR_GENERATION_CAS_MISMATCH"),
            (replace(self.task,start_ticks=0),"BEFORE_PROCESS_IDENTITY_MISSING"),
            (replace(self.task,ppid=0),"BEFORE_PROCESS_IDENTITY_MISSING")):
            with self.subTest(reason=reason):
                self.denied(replace(self.e,before=(child,)),reason)
    def test_duplicate_orphan_pid_reuse_and_socket_inventory(self):
        self.denied(replace(self.e,before=(self.task,self.task)),"BEFORE_DUPLICATE_PID_STARTTICKS")
        self.denied(replace(self.e,before=(self.task,replace(self.task,pid=125))),"BEFORE_DUPLICATE_SOCKET_INODE")
        self.denied(replace(self.e,before=(self.task,),after=(replace(self.task,start_ticks=1000),)),"AFTER_PID_REUSE_OR_REBOOT")
        self.denied(replace(self.e,after=(self.task,)),"LEGACY_DESCENDANTS_STILL_LIVE_OR_ZOMBIE")
    def test_full_global_scope_and_missing_actor_denied(self):
        self.denied(replace(self.e,scope="/"),"CGROUP_SCOPE_UNSEALED")
        self.denied(replace(self.e,entries=self.e.entries[:-1]),"LEGACY_SEVEN_ENTRYPOINTS_NOT_EXACTLY_SEALED")
if __name__=="__main__":
 unittest.main()
