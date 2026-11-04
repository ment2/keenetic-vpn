"""RC37 release-gate regression tests. Pure synthetic JSON, NO router access."""
import json
import unittest
from xray.lab.rc37_live_vs_pending_candidate_gate import (
    BLOCKERS, review, sanitized_dict,
)


def config(*tags, identities=None, fallback=None):
    identities = identities or {}
    out = []
    for tag in tags:
        out.append({
            "protocol": "vless", "tag": tag,
            "settings": {
                "vnext": [{
                    "address": identities.get(tag, tag + ".example.test"),
                    "port": 443,
                    "users": [{"id": "PRIVATE-SYNTHETIC-" + tag}],
                }]
            },
            "streamSettings": {"network": "grpc", "security": "tls"},
        })
    return json.dumps({
        "outbounds": out + [{"protocol": "blackhole", "tag": "blocked"}],
        "routing": {"balancers": [{
            "tag": "auto", "selector": ["vpn"],
            "fallbackTag": fallback if fallback is not None else (tags[0] if tags else ""),
        }]},
    })


class RC37Tests(unittest.TestCase):
    def setUp(self):
        self.live = config("vpn01", "vpn02", "vpn04", "vpn05", "vpn06", "vpn07", "vpn09")
        self.new = config("vpn01", "vpn02", "vpn04", "vpn05", "vpn09")

    def test_pending_equal_never_means_active(self):
        r = review(self.live, self.new, self.new)
        self.assertEqual(r.decision, "APPLY_REQUIRED_BUT_BLOCKED")
        self.assertTrue(r.candidate_equal_to_pending)
        self.assertFalse(r.candidate_equal_to_live)
        self.assertFalse(r.production_authorized)
        self.assertEqual(r.router_commands, ())
        self.assertEqual(r.removed_tags, ("vpn06", "vpn07"))

    def test_active_unknown_bars_claimed_preservation(self):
        r = review(self.live, self.new, self.new)
        self.assertEqual(r.reason, "ACTUAL_ACTIVE_ENDPOINT_UNOBSERVED")
        self.assertFalse(r.active_endpoint_known)

    def test_when_verified_active_retained_still_block_first_migration(self):
        r = review(self.live, self.new, self.new, active_tag="vpn01",
                   observed_live_owner=True)
        self.assertEqual(r.decision, "APPLY_REQUIRED_BUT_BLOCKED")
        self.assertEqual(r.reason, "STAGED_KEEP")
        self.assertTrue(r.active_endpoint_known)
        self.assertGreater(len(r.release_blockers), 5)

    def test_active_retired_must_switch_only_new_flows_still_blocked(self):
        r = review(self.live, self.new, self.new, active_tag="vpn06",
                   observed_live_owner=True)
        self.assertEqual(r.reason, "STAGED_SWITCH_NEW_FLOWS")
        self.assertFalse(r.production_authorized)

    def test_same_live_and_new_skip_even_without_pending(self):
        r = review(self.live, self.live)
        self.assertEqual(r.decision, "DISK_UNCHANGED_RUNTIME_UNVERIFIED")
        self.assertFalse(r.runtime_config_verified)
        self.assertTrue(r.candidate_equal_to_live)
        self.assertIsNone(r.candidate_equal_to_pending)

    def test_pending_differs_but_live_equal_still_skip(self):
        r = review(self.live, self.live, self.new)
        self.assertEqual(r.decision, "DISK_UNCHANGED_RUNTIME_UNVERIFIED")
        self.assertFalse(r.candidate_equal_to_pending)

    def test_json_key_order_is_not_a_change(self):
        parsed = json.loads(self.live)
        reordered = json.dumps(parsed, sort_keys=True)
        self.assertEqual(review(self.live, reordered).decision, "DISK_UNCHANGED_RUNTIME_UNVERIFIED")

    def test_unchanged_with_fresh_runtime_witness_skips(self):
        r = review(self.live, self.live, running_config_verified=True)
        self.assertEqual(r.decision, "SKIP_UNCHANGED")
        self.assertTrue(r.runtime_config_verified)
        self.assertEqual(r.release_blockers, ())

    def test_runtime_readback_is_not_claimed_by_pending_equality(self):
        r = review(self.live, self.new, self.new)
        self.assertFalse(r.runtime_config_verified)
        self.assertIn("FRESH_PER_NODE_OPENAI_ATTESTATIONS_NOT_VERIFIED_BY_MODEL", r.release_blockers)

    def test_tag_reuse_for_new_endpoint_detected(self):
        c = json.loads(self.new)
        c["outbounds"][0]["settings"]["vnext"][0]["address"] = "changed.example.test"
        result = review(self.live, json.dumps(c), json.dumps(c))
        self.assertEqual(result.reason, "TAG_REUSED_FOR_DIFFERENT_ENDPOINT")
        self.assertEqual(result.identity_conflicts, ("vpn01",))

    def test_credentials_change_detected_without_exposure(self):
        c = json.loads(self.live)
        c["outbounds"][0]["settings"]["vnext"][0]["users"][0]["id"] = "PRIVATE-NEW-UUID"
        result = sanitized_dict(review(self.live, json.dumps(c)))
        self.assertEqual(result["identity_conflicts"], ["vpn01"])
        self.assertNotIn("PRIVATE", str(result))
        self.assertFalse(result["production_authorized"])

    def test_empty_candidate_rejected(self):
        r = review(self.live, config())
        self.assertEqual(r.decision, "REJECT_CANDIDATE")
        self.assertEqual(r.reason, "EMPTY_QUALIFIED_POOL")

    def test_fallback_outside_qualified_rejected(self):
        r = review(self.live, config("vpn01", fallback="vpn07"))
        self.assertEqual(r.decision, "REJECT_CANDIDATE")
        self.assertEqual(r.reason, "FALLBACK_OUTSIDE_QUALIFIED_POOL")

    def test_duplicate_vless_tag_rejected(self):
        with self.assertRaises(ValueError):
            review(self.live, config("vpn01", "vpn01"))

    def test_non_json_is_rejected(self):
        with self.assertRaises(ValueError):
            review(self.live, "not-json")

    def test_changing_candidate_order_is_not_free(self):
        # Outbound order can influence fallback/leastPing semantics; preserving
        # old sessions cannot be proven by a set comparison alone.
        reordered = config("vpn09", "vpn07", "vpn06", "vpn05", "vpn04", "vpn02", "vpn01")
        r = review(self.live, reordered)
        self.assertEqual(r.decision, "APPLY_REQUIRED_BUT_BLOCKED")

    def test_every_blocker_retained_if_pending_already_matches(self):
        r = review(self.live, self.new, self.new)
        self.assertEqual(r.release_blockers, BLOCKERS)
        self.assertIn("XRAY_UDP_OWNER_INVENTORY_INCOMPLETE", r.release_blockers)


if __name__ == "__main__":
    unittest.main()
