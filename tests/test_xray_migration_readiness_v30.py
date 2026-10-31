"""Release gate must fail closed until every live requirement is independently proven."""
from dataclasses import fields, replace
import unittest
from xray.lab.migration_readiness_v30 import Evidence, assess


class MigrationReadinessTests(unittest.TestCase):
    def test_default_baseline_denied(self):
        r = assess(Evidence())
        self.assertEqual(r["decision"], "BLOCKED")
        self.assertFalse(r["deploy_authorized"])
        self.assertEqual(r["production_commands"], [])

    def test_every_gate_is_mandatory(self):
        fully = Evidence(**{f.name: True for f in fields(Evidence)})
        for f in fields(Evidence):
            result = assess(replace(fully, **{f.name: False}))
            self.assertEqual(result["decision"], "BLOCKED", f.name)
            self.assertIn(f.name, result["missing_gates"])

    def test_all_flags_still_require_human_approval(self):
        fully = Evidence(**{f.name: True for f in fields(Evidence)})
        r = assess(fully)
        self.assertEqual(r["decision"], "READY_FOR_SEPARATE_OWNER_APPROVAL")
        self.assertFalse(r["deploy_authorized"])
        self.assertEqual(r["production_commands"], [])
        self.assertFalse(r["is_real_router_evidence"])

    def test_live_audit_alone_never_enough(self):
        r = assess(Evidence(live_pid_and_ticks=True, live_config_and_binary_hashes=True))
        self.assertIn("watchdog_pid_scoped_and_fenced", r["missing_gates"])
        self.assertIn("tproxy_fwmark_table100_kernel_proven", r["missing_gates"])

    def test_first_migration_with_legacy_killall_blocked(self):
        fully = Evidence(**{f.name: True for f in fields(Evidence)})
        r = assess(replace(fully, no_global_killall_on_any_active_path=False))
        self.assertEqual(r["decision"], "BLOCKED")

    def test_socks_only_without_tproxy_blocked(self):
        fully = Evidence(**{f.name: True for f in fields(Evidence)})
        r = assess(replace(fully, both_ingress_protocols_exclusive_handoff_proven=False))
        self.assertEqual(r["decision"], "BLOCKED")

    def test_lack_of_udp_blocks(self):
        fully = Evidence(**{f.name: True for f in fields(Evidence)})
        r = assess(replace(fully, udp_end_to_end_proven=False))
        self.assertEqual(r["decision"], "BLOCKED")

    def test_without_offline_rollback_bundle_blocked(self):
        fully = Evidence(**{f.name: True for f in fields(Evidence)})
        r = assess(replace(fully, backup_restorable_locally=False))
        self.assertEqual(r["decision"], "BLOCKED")

    def test_outage_must_be_approved(self):
        fully = Evidence(**{f.name: True for f in fields(Evidence)})
        r = assess(replace(fully, acceptable_outage_confirmed=False))
        self.assertEqual(r["decision"], "BLOCKED")

    def test_no_direct_fallback(self):
        fully = Evidence(**{f.name: True for f in fields(Evidence)})
        r = assess(replace(fully, no_direct_provider_fallback=False))
        self.assertEqual(r["decision"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
