"""RC37 maintenance outage cannot override physical safety HARD NO-GO."""
import unittest
from dataclasses import fields
from xray.lab.rc37_maintenance_window_release_gate import (
    MaintenanceEvidence, review,
)


class MaintenanceGateTests(unittest.TestCase):
    def test_owner_outage_consent_alone_is_not_authorization(self):
        evidence = MaintenanceEvidence(owner_approved_outage=True)
        outcome = review(evidence)
        self.assertEqual(outcome["decision"], "HARD_NO_GO_FIRST_MIGRATION")
        self.assertIn("MISSING_OWNER_APPROVED_EXISTING_SESSION_LOSS", outcome["missing"])
        self.assertIn("MISSING_PRODUCTION_WATCHDOG_S97_S98_S99_CRON_DESCENDANTS_FENCED", outcome["missing"])
        self.assertFalse(outcome["production_authorized"])

    def test_session_loss_consent_does_not_waive_no_leak(self):
        evidence = MaintenanceEvidence(
            owner_approved_outage=True,
            owner_approved_existing_session_loss=True,
        )
        outcome = review(evidence)
        self.assertIn("MISSING_DNS_IPV6_AND_DEFAULT_ROUTE_FAIL_CLOSED", outcome["missing"])
        self.assertIn("MISSING_VERIFIED_INDEPENDENT_OFF_USB_RESCUE", outcome["missing"])

    def test_all_synthetic_receipts_still_no_production(self):
        evidence = MaintenanceEvidence(**{
            f.name: True for f in fields(MaintenanceEvidence)
        })
        outcome = review(evidence)
        self.assertEqual(outcome["decision"], "MODEL_READY_BUT_PHYSICAL_ATTESTATION_REQUIRED")
        self.assertFalse(outcome["production_authorized"])
        self.assertFalse(outcome["model_evidence_is_physical_receipt"])
        self.assertFalse(outcome["session_continuity_guaranteed"])
        self.assertEqual(outcome["router_commands"], [])

    def test_if_live_unchanged_skip_without_touching_router(self):
        outcome = review(live_differs=False)
        self.assertEqual(outcome["decision"], "SKIP_UNCHANGED")
        self.assertFalse(outcome["requires_separate_exact_execution_review"])
        self.assertEqual(outcome["router_commands"], [])

    def test_untyped_evidence_denied(self):
        with self.assertRaises(TypeError):
            review({"owner_approved_outage": True})

    def test_no_enabled_api_cannot_claim_readiness(self):
        values = {f.name: True for f in fields(MaintenanceEvidence)}
        values["xray_api_enabled_candidate_tested_on_target_kernel"] = False
        outcome = review(MaintenanceEvidence(**values))
        self.assertIn(
            "MISSING_XRAY_API_ENABLED_CANDIDATE_TESTED_ON_TARGET_KERNEL",
            outcome["missing"],
        )
        self.assertFalse(outcome["production_authorized"])


if __name__ == "__main__":
    unittest.main()
