import unittest
from unittest.mock import patch
from monitoring.vpn_node_probe import normalize_result, probe_one

def cfg():
    return {"outbounds":[{
        "tag":"vpn01","protocol":"vless",
        "settings":{"vnext":[{"address":"example.com","port":443,"users":[{"id":"secret-uuid"}]}]},
        "streamSettings":{"network":"tcp","security":"reality","realitySettings":{"publicKey":"public-key"}}
    }]}

class ProbeTests(unittest.TestCase):
    def test_success_is_route_verified_only_with_ip(self):
        r=normalize_result("vpn01","node_test",{"status":"ok","ip":"203.0.113.1","country_code":"DE"},1.23)
        self.assertEqual(r['status'],"ok")
        self.assertTrue(r['route_verified'])
        self.assertFalse(r["latency_is_rtt"])
        self.assertEqual(r["test_duration_ms"],1230)
    def test_failure_has_no_ip(self):
        r=normalize_result("vpn01","node_test",{"status":"failed","ip":"203.0.113.1"},2)
        self.assertEqual(r["status"],"failed")
        self.assertFalse(r["route_verified"])
        self.assertIsNone(r["egress_ip"])
    def test_invalid_ip_is_failed(self):
        r=normalize_result("vpn01","node_test",{"status":"ok","ip":"bad"},1)
        self.assertFalse(r["route_verified"])
    def test_probe_handles_exception(self):
        def failing(outbound): raise RuntimeError("private data")
        r=probe_one(cfg(),"vpn01",failing)
        self.assertEqual(r["status"],"failed")
        self.assertNotIn("secret-uuid",str(r))
    def test_unknown_tag_rejected(self):
        with self.assertRaises(ValueError):probe_one(cfg(),"vpn02",lambda o:{"status":"ok"})
    def test_probe_no_uuid_leak(self):
        r=probe_one(cfg(),"vpn01",lambda o:{"status":"ok","ip":"203.0.113.1","country_code":"NL"})
        self.assertTrue(r["node_id"].startswith("node_"))
        self.assertNotIn("secret-uuid",str(r))
if __name__=="__main__":unittest.main()
