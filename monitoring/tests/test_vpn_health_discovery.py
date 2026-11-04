import unittest
from unittest.mock import patch
from monitoring.vpn_health_discovery import messages,publish_for_inventory

class TestVPNDiscovery(unittest.TestCase):
    def test_four_per_node(self):
        items=list(messages("node_0123456789abcdef0123","vpn02"))
        self.assertEqual(len(items),4)
        self.assertTrue(all("node_0123456789abcdef0123" in topic for topic,_ in items))
        self.assertTrue(all(x["expire_after"]==1800 for _,x in items))
    def test_no_invalid_ids(self):
        with self.assertRaises(ValueError):list(messages("../hi","vpn01"))
        with self.assertRaises(ValueError):list(messages("node_0123456789abcdef0123","../../bad"))
    def test_retained_discovery(self):
        inventory=[{"tag":"vpn02","node_id":"node_0123456789abcdef0123"}]
        with patch("monitoring.vpn_health_discovery.publish_once") as p:
            n=publish_for_inventory(entries=inventory,host="127.0.0.1",username="test",password="secret")
        self.assertEqual(n,4)
        self.assertTrue(all(c.kwargs["retain"] for c in p.call_args_list))
    def test_duration_not_rtt(self):
        items=dict(messages("node_0123456789abcdef0123","vpn02"))
        values=[p for t,p in items.items() if "duration" in t]
        self.assertEqual(len(values),1)
        self.assertIn("Full probe duration",values[0]["name"])
    def test_no_untrusted_secrets(self):
        self.assertNotIn("password",str(list(messages("node_0123456789abcdef0123","vpn02"))).lower())
if __name__=="__main__":unittest.main()
