"""RC11 never promote offline evidence into production approval."""
from dataclasses import replace
import unittest
from xray.lab.rc11_privileged_legacy_fencing_contract import (
    Actor, Process, ARCHIVED_SHA, LEGACY_ACTORS, BOOT, evaluate, offline_good_fixture,
)

class RC11LegacyFencing(unittest.TestCase):
    def setUp(self):
        self.e=offline_good_fixture()
    def blocked(self,e,word):
        d=evaluate(e)
        self.assertEqual(d.status,"HARD_NO_GO")
        self.assertFalse(d.deployment_authorized)
        self.assertTrue(any(word in x for x in d.reasons),d.reasons)
    def test_exact_seven_actor_inventory(self):
        self.assertEqual(len(LEGACY_ACTORS),7)
        self.assertEqual(len(ARCHIVED_SHA),5)
        self.assertEqual(evaluate(self.e).status,"OFFLINE_REVIEW_CANDIDATE_ONLY")
        self.assertFalse(evaluate(self.e).deployment_authorized)
    def test_missing_or_duplicate_actors_rejected(self):
        self.blocked(replace(self.e,actors=self.e.actors[:-1]),"SEVEN_LEGACY")
        self.blocked(replace(self.e,actors=self.e.actors+(self.e.actors[0],)),"DUPLICATE")
    def test_archived_sha_drift_rejected(self):
        a=replace(self.e.actors[0],exact_sha256="1"*64)
        self.blocked(replace(self.e,actors=(a,)+self.e.actors[1:]),"ARCHIVE_SCRIPT_SHA_CHANGED")
    def test_each_legacy_spawner_must_ack_all_fence_surfaces(self):
        for name in ("old_spawner_inhibited","boot_trigger_inhibited",
                     "cron_trigger_inhibited","no_privileged_escaping_child",
                     "ack_under_common_flock"):
            with self.subTest(flag=name):
                a=replace(self.e.actors[0],**{name:False})
                self.blocked(replace(self.e,actors=(a,)+self.e.actors[1:]),"ACTOR_REMAINS")
    def test_root_cgroup_escape_is_hard_blocker(self):
        self.blocked(replace(self.e,privileged_escape_absent_proven=False),"PRIVILEGED_CGROUP_ESCAPE")
        self.blocked(replace(self.e,kernel_capability_boundary_verified=False),"CAPABILITY_BOUNDARY")
    def test_unsealed_or_unavailable_cgroup_v1_blocks(self):
        self.blocked(replace(self.e,cgroup_v1_available=False),"CGROUP_V1")
        self.blocked(replace(self.e,cgroup_sealed_before_first_spawn=False),"CGROUP_NOT_SEALED")
        self.blocked(replace(self.e,cgroup_scope="/"),"SCOPE_UNKNOWN")
        self.blocked(replace(self.e,cgroup_membership_enumeration_complete=False),"MEMBERSHIP")
    def test_unknown_reparented_descendant_or_socket_is_never_invisible(self):
        self.blocked(replace(self.e,unknown_orphan_absent_proven=False),"UNKNOWN_REPARENTED")
        self.blocked(replace(self.e,socket_listeners_fenced=False),"TCP_UDP")
        self.blocked(replace(self.e,socket_inode_enumeration_complete=False),"SOCKET_INODE")
    def test_fail_closed_when_parent_dies_prepared_or_boot_guardian_missing(self):
        self.blocked(replace(self.e,guardian_crash_prepared_not_committed=False),"PREPARED_GENERATION")
        self.blocked(replace(self.e,independent_boot_rescue_integrity=False),"BOOT_RESCUE")
    def test_stale_guardian_generation_and_unknown_boot(self):
        self.blocked(replace(self.e,expected_generation=6),"STALE_OR_AMBIGUOUS")
        self.blocked(replace(self.e,boot_id=""),"BOOT_ID")
    def test_proc_double_scan_cannot_override_unknown_escape(self):
        self.blocked(replace(self.e,privileged_escape_absent_proven=False,
                             snapshot_before=(),snapshot_after=()),"PRIVILEGED_CGROUP_ESCAPE")
    def test_real_reparented_descendant_member_must_drain(self):
        member=Process(123,456,BOOT,self.e.cgroup_scope,(), "a"*64,False)
        self.blocked(replace(self.e,snapshot_after=(member,)),"DESCENDANTS_STILL_RUNNING")
    def test_pid_reuse_before_after_has_explicit_negative(self):
        a=Process(125,456,BOOT,self.e.cgroup_scope,(12345,),"a"*64,False)
        b=replace(a,start_ticks=457)
        self.blocked(replace(self.e,snapshot_before=(a,),snapshot_after=(b,)),"PID_REUSE")
    def test_unknown_process_identity_and_stale_boot(self):
        p=Process(123,0,BOOT,self.e.cgroup_scope,(),"",False)
        self.blocked(replace(self.e,snapshot_before=(p,)),"PID_STARTTICKS_BOOT")
        p=Process(123,456,"other-boot",self.e.cgroup_scope,(),"a"*64,False)
        self.blocked(replace(self.e,snapshot_before=(p,)),"PID_STARTTICKS_BOOT")
    def test_root_or_out_of_scope_member_rejected(self):
        p=Process(123,456,BOOT,"/other",(),"a"*64,True)
        self.blocked(replace(self.e,snapshot_before=(p,)),"DESCENDANT_OUTSIDE")
        self.blocked(replace(self.e,snapshot_before=(p,)),"ROOT_OR_PRIVILEGED")
    def test_no_global_killall_or_pid_only_signal(self):
        self.blocked(replace(self.e,no_global_killall_or_pid_only_kill=False),"GLOBAL_KILLALL")
    def test_physical_kernel_and_live_hash_require_independent_proof(self):
        self.blocked(replace(self.e,physical_ndm5_mips_tproxy_no_leak_verified=False),"PHYSICAL_MIPS")
        self.blocked(replace(self.e,exact_live_sha_verified=False),"CURRENT_LIVE_SHA")

if __name__=="__main__":
    unittest.main()
