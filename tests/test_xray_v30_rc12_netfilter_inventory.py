"""Offline RC12 discovery tests never execute MIPS binaries or touch network."""
import unittest
from xray.lab.rc12_archived_mips49_netfilter_inventory import COMPONENTS, classify
class RC12NetfilterInventory(unittest.TestCase):
    def test_mips49_target_socket_mangle_are_all_required(self):
        self.assertIn("xt_TPROXY", COMPONENTS)
        self.assertIn("xt_socket", COMPONENTS)
        self.assertIn("iptable_mangle", COMPONENTS)
    def test_missing_component_never_green(self):
        for v in ("?", "m", "n"):
            with self.subTest(config=v):
                self.assertNotIn("ACCOUNTED", classify(v, False))
                self.assertIn(classify(v, False), (
                    "CONFIG_AND_MODULE_UNVERIFIED",
                    "CONFIG_MODULE_BUT_BYTES_MISSING", "CONFIG_DISABLED"))
    def test_module_wrong_vermagic_or_elf_never_green(self):
        for d in ({}, {"kernel_vermagic_match": True},
                  {"elf32_mips_little_endian": True},
                  {"kernel_vermagic_match": False, "elf32_mips_little_endian": True}):
            self.assertEqual(classify("m", True, d),
                             "MODULE_PRESENT_BUT_VERMAGIC_OR_ARCH_UNVERIFIED")
    def test_module_matching_bytes_still_not_loaded(self):
        x = classify("m", True, {
            "kernel_vermagic_match": True, "elf32_mips_little_endian": True})
        self.assertEqual(x, "MATCHING_MIPS_MODULE_BYTES_ONLY_NOT_LOADED")
    def test_builtin_config_also_not_runtime_proof(self):
        self.assertEqual(classify("y", False),
                         "KCONFIG_BUILTIN_ONLY_RUNTIME_UNVERIFIED")
if __name__ == "__main__":
    unittest.main()
