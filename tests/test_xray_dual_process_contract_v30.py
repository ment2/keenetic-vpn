"""Offline contracts for the real-process disposable lab, no Xray launch."""
import unittest
from xray.lab.xray_v30_dual_process import config


class DualProcessContracts(unittest.TestCase):
    def test_no_public_listeners(self):
        c = config(29001, 29002, 29003)
        self.assertTrue(all(x["listen"] == "127.0.0.1" for x in c["inbounds"]))

    def test_socks_udp_not_claimed_verified(self):
        c = config(29001, 29002)
        self.assertFalse(c["inbounds"][0]["settings"]["udp"])

    def test_no_api_legacy(self):
        c = config(29001, 29002)
        self.assertNotIn("api", c)

    def test_api_candidate_only(self):
        c = config(29001, 29002, 29003)
        self.assertEqual(c["api"]["tag"], "api")

    def test_blackhole_catchall(self):
        c = config(29001, 29002)
        self.assertEqual(c["routing"]["rules"][-1]["outboundTag"], "blocked")
        self.assertEqual(c["outbounds"][-1]["protocol"], "blackhole")

    def test_no_real_vpn_credentials(self):
        c = config(29001, 29002)
        self.assertFalse(any(x["protocol"] == "vless" for x in c["outbounds"]))

    def test_distinct_ingress_can_be_provisioned(self):
        old = config(29001, 29002)
        new = config(29003, 29002, 29004)
        self.assertNotEqual(old["inbounds"][0]["port"], new["inbounds"][0]["port"])

    def test_udp_is_not_claimed_tested_by_contract(self):
        # Enabling SOCKS UDP is not an end-to-end UDP ASSOCIATE test.
        c = config(29001, 29002)
        self.assertNotIn("udp_verified", c)


if __name__ == "__main__":
    unittest.main()
