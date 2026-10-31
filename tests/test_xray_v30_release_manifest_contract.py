"""Offline versioned Xray v30 manifest: reject all release drift and authorization."""
import copy
import json
import unittest

from xray.lab import v30_release_manifest_contract as m


class V30ReleaseManifestContractTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(m.MANIFEST.read_text())

    def test_real_sources_sha256_and_git_blob_match_all_nine(self):
        result = m.verify()
        self.assertEqual(result["verified"], 9)
        self.assertEqual(result["status"], "PASS_STAGED_INTEGRITY_ONLY")
        self.assertIs(result["deployment_allowed"], False)
        self.assertIs(result["production_trial_allowed"], False)
        self.assertEqual(len(result["unresolved_gates"]), 8)

    def test_duplicate_role_fails(self):
        x = copy.deepcopy(self.data)
        x["entries"][0]["role"] = x["entries"][1]["role"]
        with self.assertRaises(m.ManifestError):
            m.verify(manifest=x)

    def test_old_archive_sha_must_match_frozen_snapshot(self):
        x = copy.deepcopy(self.data)
        next(e for e in x["entries"] if e["role"]=="S97")["legacy_snapshot_sha256"] = "0"*64
        with self.assertRaisesRegex(m.ManifestError, "archive digest"):
            m.verify(manifest=x)

    def test_each_staging_blob_hash_is_frozen(self):
        for entry in self.data["entries"]:
            with self.subTest(role=entry["role"]):
                x = copy.deepcopy(self.data)
                next(e for e in x["entries"] if e["role"]==entry["role"])["staging_git_blob"]="a"*40
                with self.assertRaises(m.ManifestError):
                    m.verify(manifest=x)

    def test_each_staging_sha256_is_frozen(self):
        for entry in self.data["entries"]:
            with self.subTest(role=entry["role"]):
                x = copy.deepcopy(self.data)
                next(e for e in x["entries"] if e["role"]==entry["role"])["staging_sha256"]="a"*64
                with self.assertRaises(m.ManifestError):
                    m.verify(manifest=x)

    def test_all_forbidden_deploy_flags_stay_false(self):
        for key, value in [
            ("deployment_authorized", True),
            ("production_trial_authorized", True),
            ("status", "APPROVED"),
            ("default_action", "allow")]:
            with self.subTest(key=key):
                x = copy.deepcopy(self.data)
                x[key] = value
                with self.assertRaises(m.ManifestError):
                    m.verify(manifest=x)

    def test_missing_any_release_gate_is_no_go(self):
        for gate in m.EXPECTED_GATES:
            with self.subTest(gate=gate):
                x=copy.deepcopy(self.data)
                x["required_release_gates"].remove(gate)
                with self.assertRaises(m.ManifestError):
                    m.verify(manifest=x)

    def test_shared_flock_mutation_is_no_go(self):
        x=copy.deepcopy(self.data)
        x["shared_lock"]="/opt/var/run/other.lock"
        with self.assertRaisesRegex(m.ManifestError, "shared actor mutex"):
            m.verify(manifest=x)

    def test_legacy_canary_sha_stays_separately_pinned(self):
        x=copy.deepcopy(self.data)
        old=next(e for e in x["entries"] if e["role"]=="legacy_canary")
        old["staging_sha256"]="0"*64
        with self.assertRaises(m.ManifestError):
            m.verify(manifest=x)

    def test_escape_and_symlink_path_defense(self):
        for path in ("../outside", "/etc/passwd", "xray//staging/file",
                     "xray/staging/../../etc/passwd"):
            with self.subTest(path=path):
                with self.assertRaises(m.ManifestError):
                    m.checked_file(m.ROOT, path)

    def test_cli_has_no_trial_or_deploy(self):
        import subprocess,sys
        p=subprocess.run([sys.executable, "-m",
            "xray.lab.v30_release_manifest_contract", "--trial"],capture_output=True)
        self.assertNotEqual(p.returncode,0)
        self.assertIn(b"unrecognized arguments", p.stderr)

    def test_exact_roles_and_archive_set(self):
        self.assertEqual(len(m.EXPECTED),9)
        self.assertEqual(set(m.ARCHIVE),{"S97","S98","S99","watchdog","wifi_rules"})


if __name__ == "__main__":
    unittest.main()
