import unittest
from monitoring.telemetry import stable_node_id, validate_measurement, mqtt_topic

class TestTelemetry(unittest.TestCase):
    def event(self):
        return dict(node_id=stable_node_id(address="a.test",port=443,network="tcp",transport="tcp"),tag="vpn01",checked_at="2026-11-04T08:30:00Z",route_verified=True,status="ok",rtt_ms=40.5,egress_ip="203.0.113.3",probe="openai_http")
    def test_stable_across_alias_reordering(self):
        a=stable_node_id(address="EXAMPLE.ORG",port=443,network="tcp",transport="reality",public_key="public-key")
        b=stable_node_id(address="example.org.",port=443,network="TCP",transport="REALITY",public_key="public-key")
        self.assertEqual(a,b)
    def test_different_servers(self):
        self.assertNotEqual(stable_node_id(address="a.test",port=443,network="tcp",transport="tcp"), stable_node_id(address="b.test",port=443,network="tcp",transport="tcp"))
    def test_invalid_port(self):
        with self.assertRaises(ValueError):stable_node_id(address="a.test",port=0,network="tcp",transport="tcp")
    def test_allowlisted(self):
        self.assertEqual(validate_measurement(self.event())["schema"],1)
    def test_no_unverified_success(self):
        x=self.event();x["route_verified"]=False
        with self.assertRaises(ValueError):validate_measurement(x)
    def test_no_secret_fields(self):
        x=self.event();x["vless_uuid"]="secret"
        with self.assertRaises(ValueError):validate_measurement(x)
    def test_invalid_rtt(self):
        x=self.event();x["rtt_ms"]=-1
        with self.assertRaises(ValueError):validate_measurement(x)
    def test_invalid_ip(self):
        x=self.event();x["egress_ip"]="not-ip"
        with self.assertRaises(ValueError):validate_measurement(x)
    def test_mqtt_topic(self):
        self.assertIn("/openai_http",mqtt_topic(self.event()))
    def test_no_naive_timestamp(self):
        x=self.event();x["checked_at"]="2026-11-04T08:30:00"
        with self.assertRaises(ValueError):validate_measurement(x)

if __name__=="__main__":unittest.main()
