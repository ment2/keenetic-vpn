"""Staging release-gate tests, not a router cutover authorization."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from xray.staging import v30_cooperative_canary as canary
from xray.staging.v30_supervisor_core import FenceError, supervisor_lock
from xray.staging.v30_supervisor_service import RouterPaths
from xray.lab import v30_partial_upgrade_recovery as upgrade


class CooperativeReleaseContracts(unittest.TestCase):
    def test_broker_canary_and_five_actors_use_exact_shared_lock(self):
        self.assertEqual(canary.SHARED_LOCK, RouterPaths.lock)
        self.assertEqual(set(x["role"] for x in canary.actor_contract()),
                         {"S97", "S98", "watchdog", "cutover", "guardian"})

    def test_staging_bundle_uses_all_five_shell_entrypoints(self):
        report = canary.release_bundle_checks()
        self.assertEqual(set(report["template_sha256"]), set(canary.TEMPLATES))
        self.assertEqual(len(report["actors"]), 5)
        for digest in report["template_sha256"].values():
            self.assertRegex(digest, r"^[0-9a-f]{64}$")

    def test_broker_canary_release_never_claims_prod_ready(self):
        data = canary.release_bundle_checks()
        for key in ("production_trial_allowed", "installed_canary_compatible",
                    "legacy_supervisors_replaced", "guardian_reboot_verified"):
            self.assertIs(data[key], False)

    def test_unfenced_legacy_writers_refuse_lock(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(FenceError, "legacy restart"):
                with canary.coordinated_trial_lock(lock=Path(d) / "lock"):
                    pass

    def test_different_lock_incompatible_even_if_writer_fenced(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(FenceError, "different lock"):
                with canary.coordinated_trial_lock(lock=Path(d) / "lock",
                                                    no_legacy_writers=True):
                    pass

    def test_actual_cli_rejects_trial(self):
        run = subprocess.run([sys.executable, "-m",
            "xray.staging.v30_cooperative_canary", "--trial"],
            capture_output=True, text=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("unrecognized arguments", run.stderr)

    def test_offline_cli_reports_no_trial(self):
        run = subprocess.run([sys.executable, "-m",
            "xray.staging.v30_cooperative_canary", "--offline-plan"],
            capture_output=True, text=True, check=True)
        self.assertIs(json.loads(run.stdout)["production_trial_allowed"], False)

    def test_partial_upgrade_staging_rejects_untrusted_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "partial"
            upgrade.prepare(root)
            manifest = json.loads((root / "manifest.json").read_text())
            (root / "active" / "S98xray-wifi").write_text("UNKNOWN UNAPPROVED")
            with self.assertRaisesRegex(FenceError, "unexpected target bytes"):
                upgrade.preflight(root, manifest)

    def test_partial_upgrade_staging_refuses_symlink_target(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "partial"
            upgrade.prepare(root)
            path = root / "active" / "S99xray-watchdog"
            path.unlink()
            path.symlink_to(root / "backup" / "S99xray-watchdog")
            with self.assertRaises(FenceError):
                upgrade.preflight(root, json.loads((root / "manifest.json").read_text()))

    def test_partial_upgrade_recovery_rechecks_all_five_sha(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "partial"
            upgrade.prepare(root)
            report = json.loads((root / "manifest.json").read_text())
            self.assertTrue(upgrade.preflight(root, report))
            self.assertEqual(set(report["entries"]), set(upgrade.NAMES))


if __name__ == "__main__":
    unittest.main()
