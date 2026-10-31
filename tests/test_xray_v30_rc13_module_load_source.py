"""No silent substitution of module load for packet forwarding or production."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class RC13StaticSafety(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c=(ROOT/"xray/lab/rc13_mips49_guest_module_init.c").read_text()
        cls.s=(ROOT/"xray/lab/rc13_mips49_module_load_runner.sh").read_text()
        cls.w=(ROOT/".github/workflows/xray-v30-rc13-mips49-module-load.yml").read_text()
    def test_runner_restricted_to_disposable_qemu_no_network(self):
        self.assertIn('-net none',self.s)
        self.assertIn('DISPOSABLE_GITHUB_RUNNER_REQUIRED',self.s)
        self.assertNotIn('ssh ',self.s)
        self.assertNotIn('kubectl ',self.s)
        self.assertNotIn('killall',self.s)
    def test_guest_runs_only_module_load_not_kernel_routing(self):
        self.assertIn('SYS_init_module',self.c)
        self.assertIn('HARD_NO_GO_TCP_UDP_PACKET_PATH_NOT_EXECUTED',self.c)
        self.assertNotIn('system(',self.c)
        self.assertNotIn('iptables ',self.c)
        self.assertNotIn('route add',self.c)
    def test_runner_requires_in_guest_success_not_just_qemu_zero(self):
        self.assertIn('PASS_REAL_MIPS49_KERNEL_MODULE_LOAD_DISPOSABLE_GUEST_ONLY',self.s)
        self.assertIn('REAL_MIPS49_NETFILTER_XTABLES_TPROXY_MODULES_LOADED',self.s)
        self.assertIn('HARD_NO_GO_REAL_MIPS_TCP_UDP_PACKET_PATH_AND_PHYSICAL_HARDWARE',self.s)
    def test_workflow_feature_only_and_no_deploy(self):
        self.assertIn('feature/xray-v30-stable-tcp-ingress-lab-20261031',self.w)
        self.assertIn('contents: read',self.w)
        self.assertNotIn('keenetic-control',self.w)
if __name__=="__main__":
    unittest.main()
