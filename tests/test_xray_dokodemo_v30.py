"""Offline contracts for loopback dokodemo TCP/UDP; not real kernel TPROXY."""
import unittest
from xray.lab.xray_v30_dokodemo_lab import dokodemo_config
from xray.lab.watchdog_policy_v30 import decide, Observation, Identity


class DokodemoSafetyContracts(unittest.TestCase):
    def setUp(self):
        self.c = dokodemo_config(29011, 29012, 29013, 29014)

    def test_loopback_listeners(self):
        self.assertEqual([i["listen"] for i in self.c["inbounds"]],
                         ["127.0.0.1", "127.0.0.1"])

    def test_protocols_separate(self):
        self.assertEqual([i["settings"]["network"] for i in self.c["inbounds"]],
                         ["tcp", "udp"])

    def test_no_claim_of_tproxy(self):
        self.assertFalse(any(i["settings"]["followRedirect"] for i in self.c["inbounds"]))

    def test_destinations_restricted_loopback(self):
        self.assertTrue(all(i["settings"]["address"] == "127.0.0.1"
                            for i in self.c["inbounds"]))

    def test_no_unrestricted_fallback(self):
        self.assertEqual(self.c["outbounds"][-1]["protocol"], "blackhole")
        self.assertEqual(self.c["routing"]["rules"][-1]["outboundTag"], "blocked")

    def test_lab_freedom_is_not_internet(self):
        self.assertEqual(self.c["outbounds"][0]["protocol"], "freedom")
        self.assertEqual(self.c["routing"]["rules"][0]["inboundTag"],
                         ["lab-tcp", "lab-udp"])

    def test_no_real_credentials(self):
        self.assertFalse(any(i.get("protocol") == "vless" for i in self.c["outbounds"]))

    def test_watchdog_gate_blocks_missing_udp(self):
        i = Identity(1, 2)
        d = decide(Observation(expected=i, observed=i, tproxy_udp_ready=False))
        self.assertEqual(d.action, "request_operator_recovery")
        self.assertFalse(d.sends_signal)


if __name__ == "__main__":
    unittest.main()
