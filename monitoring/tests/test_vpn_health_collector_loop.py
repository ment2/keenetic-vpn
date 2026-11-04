import io
import unittest
from unittest.mock import patch
from monitoring.vpn_health_collector_loop import one_round, monitor

def cfg():
    return {"outbounds":[{
        "protocol":"vless","tag":"vpn01",
        "settings":{"vnext":[{"address":"server.example","port":443,"users":[{"id":"secret-user"}]}]},
        "streamSettings":{"network":"tcp","security":"reality","realitySettings":{"publicKey":"public-key"}}
    }]}

class HealthLoopTests(unittest.TestCase):
    def test_no_publish_by_default(self):
        s=io.StringIO()
        with patch("monitoring.vpn_health_collector_loop.publish_once") as mqtt:
            result=one_round(cfg(),lambda o:{"status":"ok","ip":"203.0.113.10","country_code":"DE"},sink=s)
            mqtt.assert_not_called()
        self.assertEqual(result,[("vpn01","ok")])
        self.assertNotIn("secret-user",s.getvalue())
    def test_publish_optin_and_node_topic(self):
        with patch("monitoring.vpn_health_collector_loop.publish_once") as mqtt:
            result=one_round(cfg(),lambda o:{"status":"ok","ip":"203.0.113.10"},publish=True,password="test")
        self.assertEqual(result,[("vpn01","ok")])
        self.assertIn("/health",mqtt.call_args.kwargs["topic"])
        self.assertTrue(mqtt.call_args.kwargs["topic"].startswith("keenetic/vpn-monitor/v1/node_"))
    def test_failed_mqtt_publish_does_not_record(self):
        s=io.StringIO()
        with patch("monitoring.vpn_health_collector_loop.publish_once",side_effect=ConnectionError("broker down")):
            result=one_round(cfg(),lambda o:{"status":"ok","ip":"203.0.113.10"},publish=True,password="test",sink=s)
        self.assertEqual(result,[("vpn01","error:ConnectionError")])
        self.assertEqual(s.getvalue(),"")
    def test_invalid_interval(self):
        with self.assertRaises(ValueError):monitor(interval_s=1,max_cycles=1,history_dir="/tmp/nonexistent-unused")
if __name__=="__main__":unittest.main()
