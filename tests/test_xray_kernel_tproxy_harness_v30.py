"""Nonexecuting integrity contracts for disposable kernel-TPROXY netns harness."""
from pathlib import Path
import subprocess
import unittest


SCRIPT = Path("xray/lab/xray_v30_kernel_tproxy_netns.sh")


class KernelTproxyHarnessContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = SCRIPT.read_text(encoding="utf-8")

    def test_bash_syntax(self):
        subprocess.run(["bash", "-n", str(SCRIPT)], check=True, timeout=3)

    def test_runner_only_guard(self):
        for item in ('GITHUB_ACTIONS', 'RUNNER_TEMP', '--run',
                     '/opt/etc/xray/config.json', '/opt/etc/init.d/S97xray'):
            self.assertIn(item, self.script)

    def test_isolated_namespaces_only(self):
        self.assertIn('sudo ip netns add "$ns"', self.script)
        self.assertIn('sudo ip netns del xv30g', self.script)
        self.assertIn('sudo ip netns exec xv30g iptables', self.script)

    def test_tproxy_both_protocols(self):
        self.assertIn("for proto in tcp udp", self.script)
        self.assertIn("-j TPROXY --on-port 12345", self.script)
        self.assertIn('"followRedirect":true', self.script)
        self.assertIn('"tproxy":"tproxy"', self.script)

    def test_kernel_policy(self):
        self.assertIn("iptables -P FORWARD DROP", self.script)
        self.assertIn("table 100 priority 20000", self.script)
        self.assertIn("--tproxy-mark 0x40000000/0x40000000", self.script)
        self.assertNotIn("FORWARD ACCEPT", self.script)

    def test_no_service_mutation(self):
        self.assertNotIn("S97xray restart", self.script)
        self.assertNotIn("killall xray", self.script)
        self.assertNotIn("systemctl restart", self.script)
        self.assertNotIn("uci commit", self.script)

    def test_no_prod_port_overwrite(self):
        self.assertNotIn("127.0.0.1:10808", self.script)
        self.assertNotIn("/opt/etc/xray/config.pending.json", self.script)

    def test_cleanup(self):
        self.assertIn("trap cleanup EXIT", self.script)
        self.assertIn("sudo ip netns del xv30c", self.script)
        self.assertIn("sudo ip netns del xv30s", self.script)


if __name__ == "__main__":
    unittest.main()
