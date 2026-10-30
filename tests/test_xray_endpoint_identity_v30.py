"""Offline stable endpoint fingerprint tests. All credentials synthetic."""
import importlib.util
from pathlib import Path
import sys
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "xray/lab/endpoint_identity_v30.py"
spec = importlib.util.spec_from_file_location("endpoint_identity_v30", SOURCE)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
KEY = b"synthetic-offline-test-key-not-for-production-123"


def outbound(tag="vpn01", user="test-user", host="test.invalid"):
    return {
        "tag": tag, "protocol": "vless",
        "settings": {"vnext": [{"address": host, "port": 443,
                                "users": [{"id": user, "encryption": "none"}]}]},
        "streamSettings": {"network": "grpc", "security": "reality",
                           "realitySettings": {"serverName": "test.invalid",
                                              "publicKey": "synthetic"}},
    }


class EndpointIdentityTests(unittest.TestCase):
    def test_positional_tag_does_not_change_identity(self):
        self.assertEqual(module.identity(outbound("vpn01"), KEY),
                         module.identity(outbound("vpn09"), KEY))

    def test_json_key_order_does_not_change_identity(self):
        original = outbound()
        shuffled = dict(reversed(list(original.items())))
        self.assertEqual(module.identity(original, KEY), module.identity(shuffled, KEY))

    def test_credentials_change_identity(self):
        self.assertNotEqual(module.identity(outbound(user="old"), KEY),
                            module.identity(outbound(user="new"), KEY))

    def test_host_change_identity(self):
        self.assertNotEqual(module.identity(outbound(host="a.invalid"), KEY),
                            module.identity(outbound(host="b.invalid"), KEY))

    def test_stable_tag_is_safe_and_short(self):
        tag = module.stable_tag(outbound(), KEY)
        self.assertTrue(tag.startswith("vpn-"))
        self.assertEqual(len(tag), 28)
        self.assertNotIn("test-user", tag)

    def test_duplicate_subscription_endpoint_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            module.tag_map([outbound("vpn01"), outbound("vpn99")], KEY)

    def test_subscription_reorder_keeps_tags(self):
        a = outbound(host="a.invalid")
        b = outbound(host="b.invalid")
        self.assertEqual(module.tag_map([a, b], KEY),
                         module.tag_map([b, a], KEY))

    def test_hmac_key_is_required(self):
        with self.assertRaises(ValueError):
            module.identity(outbound(), b"weak")

    def test_non_vless_is_rejected(self):
        with self.assertRaises(ValueError):
            module.identity({"protocol": "freedom", "settings": {}}, KEY)

    def test_key_rotation_changes_identity(self):
        self.assertNotEqual(module.identity(outbound(), KEY),
                            module.identity(outbound(), b"other-synthetic-offline-key-123456789"))


if __name__ == "__main__":
    unittest.main()
