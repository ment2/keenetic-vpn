import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from monitoring.openai_node_probe import probe_one, load_probe
from monitoring.openai_health_collector_loop import one_round, monitor

def cfg():
    return {"outbounds":[{"tag":"vpn01","protocol":"vless",
        "settings":{"vnext":[{"address":"example.com","port":443,"users":[{"id":"private-uuid"}]}]},
        "streamSettings":{"network":"tcp","security":"reality","realitySettings":{"publicKey":"pubkey"}}}]}

class OpenAIProbeTests(unittest.TestCase):
    def test_reachable_only_on_positive_evidence(self):
        ok=probe_one(cfg(),"vpn01",lambda outbound:"reachable")
        self.assertEqual(ok["status"],"reachable")
        self.assertTrue(ok["route_verified"])
        self.assertFalse(ok["latency_is_rtt"])
        self.assertNotIn("private-uuid",str(ok))

    def test_failed_route_has_no_positive_witness(self):
        for status in ("network_error","timeout","xray_start_failed","http_403",None):
            event=probe_one(cfg(),"vpn01",lambda _:status)
            self.assertNotEqual(event["status"],"reachable")
            self.assertFalse(event["route_verified"])

    def test_exception_fails_closed(self):
        def fail(_):raise RuntimeError("private-uuid")
        event=probe_one(cfg(),"vpn01",fail)
        self.assertEqual(event["status"],"unknown")
        self.assertFalse(event["route_verified"])
        self.assertNotIn("private-uuid",str(event))

    def test_single_outbound_only(self):
        seen=[]
        def callback(o):
            seen.append(o["tag"])
            return "reachable"
        probe_one(cfg(),"vpn01",callback)
        self.assertEqual(seen,["vpn01"])

    def test_one_round_does_not_publish_by_default(self):
        with patch("monitoring.openai_health_collector_loop.publish_once") as publish:
            sink=io.StringIO()
            result=one_round(cfg(),lambda _: "reachable",sink=sink)
            self.assertEqual(result,[("vpn01","reachable")])
            self.assertEqual(json.loads(sink.getvalue())["status"],"reachable")
            publish.assert_not_called()

    def test_publish_route_and_safe_payload(self):
        with patch("monitoring.openai_health_collector_loop.publish_once") as publish:
            one_round(cfg(),lambda _: "reachable",publish=True,password="secret")
        a=publish.call_args.kwargs
        self.assertIn("/openai_http",a["topic"])
        self.assertNotIn("secret",str(a["payload"]))
        self.assertTrue(a["payload"]["route_verified"])

    def test_missing_password_fails_closed(self):
        sink=io.StringIO()
        results=one_round(cfg(),lambda _: "reachable",publish=True,password=None,sink=sink)
        self.assertEqual(results,[("vpn01","error:ValueError")])
        self.assertEqual(json.loads(sink.getvalue())["status"], "reachable")

    def test_mqtt_outage_preserves_history(self):
        sink=io.StringIO()
        with patch("monitoring.openai_health_collector_loop.publish_once", side_effect=OSError("offline")):
            result=one_round(cfg(),lambda _: "reachable",publish=True,password="secret",sink=sink)
        self.assertEqual(result,[("vpn01","error:OSError")])
        self.assertEqual(json.loads(sink.getvalue())["status"], "reachable")
        self.assertNotIn("secret", sink.getvalue())

    def test_invalid_interval_never_reads_config(self):
        with self.assertRaises(ValueError):
            monitor(interval_s=60,max_cycles=1,config_path="/does-not-exist")
        
    def test_load_probe_requires_check_function(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"missing.py"
            p.write_text("def other(outbound): pass\n")
            with self.assertRaises(RuntimeError):
                load_probe(str(p))

if __name__=="__main__":unittest.main()
