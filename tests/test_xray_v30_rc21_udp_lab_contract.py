"""RC21 disposable QEMU-only UDP bind-collision and isolation contracts.
These tests do not assert real MIPS packet success or production suitability.
"""
import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNNER = ROOT / "xray/lab/rc21_mips49_xray_tproxy_runner.sh"
GUEST = ROOT / "xray/lab/rc21_mips49_xray_packet.sh"
ECHO = ROOT / "xray/lab/rc19_mips49_tcpudp_echo.c"


class RCTproxyUdpContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = RUNNER.read_text()
        cls.guest = GUEST.read_text()
        cls.echo = ECHO.read_text()
        marker = "cat >\"$W/initramfs/etc/xray.json\" <<'JSON'\n"
        assert marker in cls.runner
        config = cls.runner.split(marker, 1)[1].split("\nJSON\n", 1)[0]
        cls.config = json.loads(config)

    def test_original_destination_stays_intercepted(self):
        self.assertIn("hostfwd=tcp:127.0.0.1:19191-:19191", self.runner)
        self.assertIn("hostfwd=udp:127.0.0.1:19191-:19191", self.runner)
        self.assertIn("--dport 19191 -j TPROXY --on-port 12345", self.guest)
        self.assertTrue(self.config["inbounds"][0]["settings"]["followRedirect"])
        self.assertEqual(self.config["inbounds"][0]["streamSettings"]["sockopt"]["tproxy"], "tproxy")

    def test_backend_is_separate_guest_loopback_port(self):
        self.assertIn("-DPORT=19292", self.runner)
        self.assertIn("#ifndef PORT", self.echo)
        self.assertEqual(self.config["outbounds"][0]["settings"]["redirect"], "127.0.0.1:19292")
        self.assertNotEqual(19191, 19292)
        self.assertIn(":4B5C ", self.guest)
        self.assertIn(":3039 ", self.guest)

    def test_no_external_network_or_production_changes(self):
        self.assertIn("-netdev user,id=isolated,restrict=on", self.runner)
        self.assertIn('"127.0.0.1",19191', self.runner)
        self.assertIn("GITHUB_ACTIONS", self.runner)
        self.assertNotIn("-netdev user,id=isolated,restrict=off", self.runner)

    def test_real_udp_result_must_be_witnessed(self):
        self.assertIn("REAL_TCP_UDP_ECHO_BYTES_PASS", self.runner)
        self.assertIn("REAL_XRAY_BACKEND_TCP_UDP_AND_TPROXY_COUNTERS", self.runner)
        self.assertIn("HARD_NO_GO_XRAY_UDP_FAKE_SOCKET_BIND_COLLISION", self.guest)
        self.assertIn("HARD_NO_GO_UDP_BACKEND_NOT_RECEIVED_WITHIN_DEADLINE", self.guest)
        self.assertIn("HARD_NO_GO_HOST_UDP_RETURN_DIRECT_FALLBACK_PHYSICAL_BOOT_RESCUE", self.guest)

    def test_guest_tproxy_same_mark_and_table(self):
        self.assertIn("fwmark 0x40000000/0x40000000 table 100", self.guest)
        self.assertEqual(self.guest.count("--tproxy-mark 0x40000000/0x40000000"), 2)
        self.assertIn("local 0.0.0.0/0 dev lo table 100", self.guest)


if __name__ == "__main__":
    unittest.main()
