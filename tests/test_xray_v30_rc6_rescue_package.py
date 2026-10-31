"""RC6 exact no-deploy shell rescue tar and tamper resistance."""
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

from xray.lab import v30_rc6_rescue_package as p

class RC6TarTests(unittest.TestCase):
    def test_repeated_build_byte_identical(self):
        self.assertEqual(p.fixed_tar(p.entries()),p.fixed_tar(p.entries()))
    def test_exact_bundle_nonexecutable_and_nonbootable(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/p.NAME
            path.write_bytes(p.fixed_tar(p.entries()))
            verdict=p.verify(path)
            self.assertEqual(verdict["status"],"VERIFIED_OFFLINE_REHEARSAL_PACKAGE_ONLY")
            self.assertEqual(verdict["originals"],5)
            self.assertFalse(verdict["bootable"])
            self.assertFalse(verdict["production_authorized"])
            with tarfile.open(path) as t:
                self.assertEqual(len(t.getmembers()),8)
                self.assertTrue(all(i.mode==0o600 for i in t.getmembers()))
    def test_modified_guardian_refused(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/p.NAME
            files=p.entries()
            files["guardian.sh"]+=b"\n# sabotage\n"
            path.write_bytes(p.fixed_tar(files))
            with self.assertRaises(ValueError):p.verify(path)
    def test_modified_original_refused_even_if_metadata_is_untouched(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/p.NAME
            files=p.entries()
            files["originals/S97.sh"]+=b"\nBAD\n"
            path.write_bytes(p.fixed_tar(files))
            with self.assertRaises(ValueError):p.verify(path)
    def test_hardware_authorization_explicitly_false(self):
        meta=json.loads(p.entries()["package-metadata.json"])
        for key in ("guardian_executable_on_keenetic_verified",
                    "guardian_usable_at_router_boot_without_entware",
                    "mounted_on_distinct_physical_device",
                    "physical_cold_boot_test_passed",
                    "filesystem_powerloss_atomicity_proven",
                    "production_authorized"):
            self.assertIs(meta[key],False)
        self.assertEqual(meta["router_commands"],[])
if __name__=="__main__":unittest.main()
