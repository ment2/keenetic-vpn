"""RC26 strict evidence-only gate. No packet or production execution."""
import unittest
from dataclasses import replace
from xray.lab.rc26_udp_legacy_cutover_gate import (
    ACTORS, Process, Witness, evaluate, synthetic_all_positive,
    current_confirmed_evidence,
)

class ReleaseBoundary(unittest.TestCase):
    def setUp(self):
        self.good=synthetic_all_positive()
    def reject(self, ev, reason):
        v=evaluate(ev)
        self.assertEqual(v["state"],"HARD_NO_GO",v)
        self.assertIn(reason,v["reasons"])
        self.assertFalse(v["production_authorized"])
        self.assertFalse(v["hardware_certified"])
        self.assertEqual(v["router_commands"],())
    def test_actual_checkpoints_remain_hard_blocked(self):
        bad=current_confirmed_evidence()
        for name in ("exact_host_udp_return_positive_control",
                     "original_destination_not_rewritten",
                     "old_tcp_conntrack_established_before_cutover",
                     "real_kernel_root_escape_fenced"):
            self.assertIn("UNPROVEN:"+name,evaluate(bad)["reasons"])
        self.assertIn("ACTUAL_PRIVILEGED_CGROUP_ESCAPE_OBSERVED",
                      evaluate(bad)["reasons"])
    def test_synthetic_green_is_only_review(self):
        x=evaluate(self.good)
        self.assertEqual(x["state"],"OFFLINE_REVIEW_CANDIDATE_ONLY")
        self.assertFalse(x["production_authorized"])
        self.assertFalse(x["real_packet_positive_control_accepted"])
    def test_individual_packet_and_physical_witness_mutations(self):
        flags=("mips49_xt_tproxy_tcp_udp_backend",
             "exact_host_udp_return_positive_control",
             "original_destination_not_rewritten",
             "distinct_backend_network_stack_proven",
             "old_tcp_conntrack_established_before_cutover",
             "old_tcp_survives_first_cutover_and_rollback",
             "no_tcp_udp_direct_fallback_after_death",
             "no_ipv4_ipv6_dns_leak","real_kernel_root_escape_fenced",
             "physical_vendor_kernel_verified",
             "independent_usb_absent_cold_boot_rescue")
        for flag in flags:
            with self.subTest(flag=flag):
                self.reject(replace(self.good,**{flag:False}),"UNPROVEN:"+flag)
    def test_mutate_each_seven_actor_approval(self):
        for idx,actor in enumerate(self.good.actors):
            for flag in ("boot_acked","cron_acked","watchdog_acked",
                         "kernel_root_fence","no_stale_writer"):
                with self.subTest(actor=actor.name,flag=flag):
                    items=list(self.good.actors)
                    items[idx]=replace(actor,**{flag:False})
                    self.reject(replace(self.good,actors=tuple(items)),
                                "UNFENCED_LEGACY_ACTOR:"+actor.name+":"+flag)
    def test_missing_or_forged_actor_shas(self):
        a=self.good.actors[0]
        items=(replace(a,observed_sha256="b"*64),)+self.good.actors[1:]
        self.reject(replace(self.good,actors=items),
                    "UNPINNED_OR_DRIFTED_LIVE_SHA:"+a.name)
        self.reject(replace(self.good,actors=self.good.actors[:-1]),
                    "SEVEN_EXACT_LEGACY_ENTRYPOINTS_UNSEALED")
    def test_generation_prepared_and_boot_fencing(self):
        self.reject(replace(self.good,expected_generation=6),
                    "GENERATION_CAS_STALE_OR_AMBIGUOUS")
        self.reject(replace(self.good,prepared_generation_replayed=True),
                    "PREPARED_JOURNAL_REPLAY")
        self.reject(replace(self.good,root_cgroup_escape_observed=True),
                    "ACTUAL_PRIVILEGED_CGROUP_ESCAPE_OBSERVED")
        self.reject(replace(self.good,boot_id="not-uuid"),"BOOT_UUID_UNTRUSTED")
    def test_pid_start_ticks_socket_inode_reuse(self):
        p=Process(77,12,500,self.good.boot_id,"c"*64,7,(100,200),False,self.good.scope)
        self.reject(replace(self.good,before=(replace(p,start_ticks=0),)),
                    "BEFORE_PID_BOOT_START_SHA_INVALID")
        self.reject(replace(self.good,before=(replace(p,generation=6),)),
                    "BEFORE_GENERATION_CAS_MISMATCH")
        self.reject(replace(self.good,before=(p,replace(p,pid=78))),
                    "BEFORE_SOCKET_INODE_UNRELIABLE")
        self.reject(replace(self.good,before=(p,),after=(replace(p,start_ticks=501),)),
                    "AFTER_PID_REUSE_OR_BOOT_CHANGE")
        self.reject(replace(self.good,after=(p,)),
                    "ORPHAN_OR_LEGACY_DESCENDANT_NOT_DRAINED")
        self.reject(replace(self.good,before=(replace(p,privileged=True),)),
                    "BEFORE_ROOT_OR_OUT_OF_SCOPE_CHILD")
    def test_no_default_green_in_absence_of_evidence(self):
        self.reject(Witness(),"SEVEN_EXACT_LEGACY_ENTRYPOINTS_UNSEALED")

if __name__=="__main__":
    unittest.main()
