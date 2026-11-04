import unittest
from unittest.mock import patch
from monitoring.homeassistant_discovery import discovery_messages, publish_discovery

class TestHADiscovery(unittest.TestCase):
    def test_four_sensors_per_interface(self):
        items=list(discovery_messages("apclii0"))
        self.assertEqual(len(items), 4)
        self.assertEqual(len(set(topic for topic,_ in items)),4)
        self.assertTrue(all(topic.endswith("/config") for topic,_ in items))
    def test_state_topic_and_expiry(self):
        for _, p in discovery_messages("br0"):
            self.assertEqual(p["state_topic"],"keenetic/vpn-monitor/v1/traffic/br0")
            self.assertEqual(p["expire_after"],240)
            self.assertEqual(p["qos"],1)
    def test_no_private_data(self):
        self.assertNotIn("password",str(list(discovery_messages("br1"))).lower())
    def test_unknown_interface_rejected(self):
        with self.assertRaises(ValueError):list(discovery_messages("../../etc/passwd"))
    def test_publish_discovery_retained(self):
        with patch("monitoring.homeassistant_discovery.publish_once") as mock:
            count=publish_discovery(host="192.168.0.169",username="test",password="secret",interfaces=("br0",))
        self.assertEqual(count,4)
        self.assertTrue(all(call.kwargs["retain"] for call in mock.call_args_list))
    def test_discovery_device_identity(self):
        devices={p["device"]["identifiers"][0] for _,p in discovery_messages("apclii0")}
        self.assertEqual(devices,{"keenetic6059_vpn_monitor"})
if __name__ == "__main__":unittest.main()
