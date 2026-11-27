import json
import os
import socket
import subprocess
import time
import unittest
from unittest.mock import Mock, patch
from monitoring import isolated_pair_probe as p

class IsolatedPairTests(unittest.TestCase):
    def test_real_kernel_listener_identity(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1",0))
            port=s.getsockname()[1]
            self.assertFalse(p.owned_listener(os.getpid(),port))
            s.listen()
            self.assertTrue(p.owned_listener(os.getpid(),port))
            self.assertFalse(p.owned_listener(99999999,port))
        self.assertFalse(p.owned_listener(os.getpid(),port))
    def test_blackhole_default_and_loopback(self):
        cfg=p.config_for({"protocol":"vless","tag":"vpn01"},12345)
        self.assertEqual(cfg["inbounds"][0]["listen"],"127.0.0.1")
        self.assertEqual(cfg["outbounds"][0]["protocol"],"blackhole")
        self.assertEqual(cfg["routing"]["rules"][0]["outboundTag"],"probe-out")
        self.assertEqual(len(cfg["outbounds"]),2)
    def test_curl_no_config_and_proxy_explicit(self):
        with patch.object(p.subprocess,"run") as run:
            p.http_request(12345,"https://api.openai.com/v1/models")
            args,kwargs=run.call_args
            self.assertEqual(args[0][1],"-q")
            self.assertIn("socks5h://127.0.0.1:12345",args[0])
            self.assertNotIn("--location",args[0])
            self.assertNotIn("--insecure",args[0])
            self.assertFalse(any(k.lower() in ("http_proxy","https_proxy","all_proxy","no_proxy") for k in kwargs["env"]))
    def test_owner_lost_during_request(self):
        with patch.object(p,"live_owner",side_effect=[True,False]), patch.object(p,"http_request",return_value=object()):
            self.assertIsNone(p.query_owned(Mock(),12345,"https://example.invalid"))
    def test_no_owner_no_http(self):
        with patch.object(p,"live_owner",return_value=False), patch.object(p,"http_request") as http:
            self.assertIsNone(p.query_owned(Mock(),12345,"https://example.invalid"))
            http.assert_not_called()
    def test_only_401(self):
        for code in (b"200",b"403",b"429",b"000"):
            self.assertEqual(p.openai_result(Mock(returncode=0,stdout=code)),"http_error")
        self.assertEqual(p.openai_result(Mock(returncode=0,stdout=b"401")),"reachable")
        self.assertEqual(p.openai_result(Mock(returncode=1,stdout=b"401")),"network_error")
    def test_geo_contract(self):
        self.assertEqual(p.geo_result(Mock(returncode=0,stdout=b"{}"))["status"],"failed")
        self.assertEqual(p.geo_result(Mock(returncode=0,stdout=json.dumps({"success":True,"ip":"203.0.113.1","country_code":"DE"}).encode()))["status"],"ok")
    def test_budget_and_abort(self):
        entries=[{"node_id":"a","tag":"vpn01"},{"node_id":"b","tag":"vpn02"}]
        probe=Mock()
        self.assertEqual(p.collect({},entries,deadline=time.monotonic()+1,probe=probe),{})
        probe.assert_not_called()
        probe.side_effect=p.CleanupError()
        with self.assertRaises(p.CleanupError):
            p.collect({},entries,deadline=time.monotonic()+200,probe=probe)
        self.assertEqual(probe.call_count,1)
