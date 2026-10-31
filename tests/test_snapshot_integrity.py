"""Offline mutation tests for the frozen 63-file production-source manifest."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from tools.verify_production_snapshot import verify


class FrozenManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="xray-frozen-manifest-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        rows = []
        for i in range(63):
            rel = f"opt/bin/synthetic-{i:02d}.sh"
            f = self.root / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(f"lab fixture {i}\n".encode())
            rows.append(f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {rel}  100644")
        (self.root / "MANIFEST.sha256").write_text(
            "# synthetic fixture; not router data\n" + "\n".join(rows) + "\n")
        self.fixture = self.root / "opt/bin/synthetic-00.sh"

    def test_pass_valid_bytes(self):
        result = verify(self.root, check_modes=False)
        self.assertEqual(result["verified_files"], 63)
        self.assertFalse(result["router_live_hashes_checked"])
        self.assertFalse(result["full_router_recovery_verified"])

    def test_modified_file_fails(self):
        self.fixture.write_bytes(b"modified")
        with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
            verify(self.root, check_modes=False)

    def test_missing_file_fails(self):
        self.fixture.unlink()
        with self.assertRaisesRegex(ValueError, "missing manifest files"):
            verify(self.root, check_modes=False)

    def test_unmanifested_file_fails(self):
        (self.root / "opt/bin/unknown.sh").write_text("unexpected")
        with self.assertRaisesRegex(ValueError, "unmanifested"):
            verify(self.root, check_modes=False)

    def test_duplicate_manifest_entry_fails(self):
        manifest = self.root / "MANIFEST.sha256"
        last = manifest.read_text().splitlines()[-1]
        manifest.write_text(manifest.read_text() + last + "\n")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            verify(self.root, check_modes=False)

    def test_forbidden_secret_path_fails(self):
        (self.root / "opt/bin/subscription.url").write_text("placeholder")
        with self.assertRaisesRegex(ValueError, "secret-bearing"):
            verify(self.root, check_modes=False)

    def test_symlink_fails(self):
        (self.root / "opt/bin/alias.sh").symlink_to(self.fixture)
        with self.assertRaisesRegex(ValueError, "symlink"):
            verify(self.root, check_modes=False)

    def test_wrong_manifest_count_fails(self):
        manifest = self.root / "MANIFEST.sha256"
        manifest.write_text("# no files\n")
        with self.assertRaisesRegex(ValueError, "count"):
            verify(self.root, check_modes=False)


if __name__ == "__main__":
    unittest.main()
