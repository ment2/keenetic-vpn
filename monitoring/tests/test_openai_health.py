import unittest
from unittest.mock import patch

from monitoring.openai_health_contract import normalize_openai_result
from monitoring.openai_health_discovery import messages, publish_for_inventory

NODE = "node_0123456789abcdef0123"


class ContractTests(unittest.TestCase):
    def make(self, raw, verified=True):
        return normalize_openai_result("vpn06", NODE, raw,
            route_verified=verified, duration_ms=3100,
            checked_at="2026-11-04T14:00:00+00:00")

    def test_only_explicit_reachable_is_positive(self):
        self.assertEqual(self.make("reachable")["status"], "reachable")
        for raw in ("ok", "HTTP 401", "network_error", {"status": "ok"}, None):
            self.assertNotEqual(self.make(raw)["status"], "reachable")

    def test_success_requires_route_witness(self):
        self.assertEqual(self.make("reachable", False)["status"], "unknown")

    def test_classify_known_failure(self):
        self.assertEqual(self.make("network_error")["status"], "network_error")

    def test_no_exceptions_or_secrets_in_publication(self):
        raw = {"status": "unexpected", "password": "do-not-leak", "uuid": "private"}
        result = self.make(raw)
        self.assertEqual(result["status"], "unknown")
        self.assertNotIn("do-not-leak", str(result))
        self.assertNotIn("private", str(result))

    def test_bad_identity_rejected(self):
        with self.assertRaises(ValueError):
            normalize_openai_result("../vpn", NODE, "reachable",
                route_verified=True, duration_ms=10)

    def test_duration_is_not_rtt(self):
        self.assertFalse(self.make("reachable")["latency_is_rtt"])
        with self.assertRaises(ValueError):
            normalize_openai_result("vpn06", NODE, "reachable",
                route_verified=True, duration_ms=True)

    def test_naive_time_fails(self):
        with self.assertRaises(ValueError):
            normalize_openai_result("vpn06", NODE, "reachable",
                route_verified=True, duration_ms=123,
                checked_at="2026-11-04T12:00:00")


class DiscoveryTests(unittest.TestCase):
    def test_three_sensors_per_node(self):
        items = list(messages(NODE, "vpn06"))
        self.assertEqual(len(items), 3)
        self.assertTrue(all(v["expire_after"] == 1800 for _,v in items))
        self.assertTrue(all(v["device"]["identifiers"] == [f"keenetic6059_{NODE}"]
                            for _,v in items))

    def test_retained_discovery_no_credentials(self):
        with patch("monitoring.openai_health_discovery.publish_once") as pub:
            n = publish_for_inventory(entries=[{"tag": "vpn06", "node_id": NODE}],
                host="192.168.0.169", username="keenetic_monitor", password="test-pass")
        self.assertEqual(n, 3)
        self.assertTrue(all(x.kwargs["retain"] is True for x in pub.call_args_list))
        self.assertNotIn("test-pass", str(list(messages(NODE, "vpn06"))))

    def test_invalid_identity(self):
        with self.assertRaises(ValueError):
            list(messages("node_bad", "vpn06"))


if __name__ == "__main__":
    unittest.main()
