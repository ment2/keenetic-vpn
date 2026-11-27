import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from monitoring import dynamic_snapshot as d

NOW = 1795788000
N1 = "node_" + "a"*20
N2 = "node_" + "b"*20
ENTRIES = [{"node_id": N1, "tag": "vpn01"}, {"node_id": N2, "tag": "vpn06"}]

def event(node=N1, kind="health", age=0, verified=True):
    return {"node_id": node, "test_kind": {"health":"isolated_xray_http204","geo":"isolated_xray_http_egress","openai":"isolated_xray_openai_http"}[kind],
            "checked_at": datetime.fromtimestamp(NOW-age,timezone.utc).isoformat(),
            "status": "reachable" if kind=="openai" else "ok", "route_verified": verified,
            "test_duration_ms": 4000, "egress_ip": "203.0.113.1", "country_code": "DE"}

class DynamicSnapshotTests(unittest.TestCase):
    def test_all_subscription_and_membership(self):
        r=d.snapshot(ENTRIES,{N2},{N1},{N1:{"health":event()}},NOW)
        self.assertEqual(r["count"],2)
        self.assertEqual(r["rows"][0][2:5],[False,True,"ok"])
        self.assertEqual(r["rows"][1][2:5],[True,False,"missing"])
    def test_stale_and_future(self):
        for age in (1801,-5):
            self.assertEqual(d.measure(event(age=age),N1,"health",NOW)[0],"stale")
    def test_route_and_identity(self):
        self.assertEqual(d.measure(event(verified=False),N1,"health",NOW)[0],"unknown")
        self.assertEqual(d.measure(event(node=N2),N1,"health",NOW)[0],"missing")
        self.assertEqual(d.measure(event(kind="openai",verified=False),N1,"openai",NOW)[0],"unknown")
    def test_independent_results(self):
        r=d.snapshot(ENTRIES,None,set(),{N1:{"openai":event(kind="openai")}},NOW)
        self.assertEqual(r["rows"][0][2:5],[None,False,"missing"])
        self.assertEqual(r["rows"][0][9],"reachable")
    def test_tag_changes_do_not_reassign(self):
        r=d.snapshot([{"node_id":N2,"tag":"vpn01"}],set(),set(),{N1:{"health":event()}},NOW)
        self.assertEqual(r["rows"][0][4],"missing")
    def test_removed_node_not_shown(self):
        r=d.snapshot(ENTRIES[:1],{N2},None,{},NOW)
        self.assertEqual(r["active_unmatched"],1)
        self.assertEqual(r["count"],1)
    def test_pending_absent_vs_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"pending.json"
            self.assertEqual(d.pool_ids(p,optional=True),set())
            self.assertIsNone(d.pool_ids(p))
            p.write_text("bad")
            self.assertIsNone(d.pool_ids(p,optional=True))
    def test_probe_failure_and_sequential(self):
        calls=[]
        def h(c,t):
            calls.append(("h",t))
            raise RuntimeError()
        def o(c,t):
            calls.append(("o",t))
            return event(kind="openai")
        r=d.run_probes({},ENTRIES,h,o)
        self.assertEqual(calls,[("h","vpn01"),("o","vpn01"),("h","vpn06"),("o","vpn06")])
        self.assertIsNone(r[N1]["health"])
    def test_atomic_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"cache"
            d.atomic_cache(p,{"a":1})
            self.assertEqual(json.loads(p.read_text()),{"a":1})
            self.assertEqual(p.stat().st_mode & 0o777,0o600)
    def test_payload_cap(self):
        with patch.object(d,"MAX_PAYLOAD",1):
            with self.assertRaises(ValueError):
                d.snapshot(ENTRIES,set(),set(),{},NOW)
    def test_discovery_expiry(self):
        self.assertEqual(d.discovery()["expire_after"],150)
        self.assertEqual(d.discovery()["json_attributes_topic"],d.TOPIC)

    def test_geo_failure_independent_of_http204(self):
        r=d.snapshot(ENTRIES,set(),set(),{N1:{"health":event(),"geo":dict(event(kind="geo"),status="failed"),"openai":event(kind="openai")}},NOW)
        row=r["rows"][0]
        self.assertEqual((row[4],row[9],row[14]),("ok","reachable","failed"))
        self.assertIsNone(row[7])
    def test_last_geo_is_stale_after_failure_and_expires(self):
        prior=dict(event(kind="geo",age=600),city="Berlin")
        merged=d.retain_geo({N1:{"last_geo":prior}},{N1:{"geo":dict(event(kind="geo"),status="failed")}},ENTRIES,now=NOW)
        r=d.snapshot(ENTRIES,set(),set(),merged,NOW)
        self.assertEqual(r["rows"][0][14:17],["stale",NOW-600,"Berlin"])
        self.assertEqual(r["rows"][0][7],"203.0.113.1")
        self.assertIsNone(d.snapshot(ENTRIES,set(),set(),merged,NOW+86401)["rows"][0][7])
    def test_address_change_does_not_inherit_geo(self):
        prior=dict(event(kind="geo"),city="Berlin")
        new=[{"node_id":N2,"tag":"vpn01"}]
        merged=d.retain_geo({N1:{"last_geo":prior}},{},new,now=NOW)
        row=d.snapshot(new,set(),set(),merged,NOW,{"vpn01":["new.example.invalid",443]})["rows"][0]
        self.assertIsNone(row[7])
        self.assertEqual(row[12:14],["new.example.invalid",443])
    def test_new_egress_replaces_previous(self):
        a=dict(event(kind="geo",age=600),city="Berlin")
        b=dict(event(kind="geo"),egress_ip="203.0.113.2",city="Paris",country_code="FR")
        merged=d.retain_geo({N1:{"last_geo":a}},{N1:{"geo":b}},ENTRIES,now=NOW)
        row=d.snapshot(ENTRIES,set(),set(),merged,NOW)["rows"][0]
        self.assertEqual((row[7],row[8],row[16]),("203.0.113.2","FR","Paris"))
    def test_invalid_geo_never_overwrites_good(self):
        prior=event(kind="geo",age=600)
        invalid=event(kind="geo",verified=False)
        merged=d.retain_geo({N1:{"last_geo":prior}},{N1:{"geo":invalid}},ENTRIES,now=NOW)
        self.assertEqual(merged[N1]["last_geo"],prior)
    def test_payload_worst_case(self):
        entries=[{"node_id":"node_%020x"%i,"tag":"vpn%02d"%i} for i in range(1,25)]
        observations={e["node_id"]:{"health":event(e["node_id"]),"openai":event(e["node_id"],kind="openai"),"geo":dict(event(e["node_id"],kind="geo"),city="𐐀"*64,egress_ip="2001:db8:ffff:ffff:ffff:ffff:ffff:ffff")} for e in entries}
        endpoints={e["tag"]:["a"*253,65535] for e in entries}
        result=d.snapshot(entries,set(),set(),observations,NOW,endpoints)
        self.assertEqual(result["count"],24)
        self.assertLessEqual(len(json.dumps(result,separators=(",",":"),ensure_ascii=True).encode()),d.MAX_PAYLOAD)
    def test_endpoint_never_contains_uri_or_credentials(self):
        def ob(address):
            return {"protocol":"vless","tag":"vpn01","settings":{"vnext":[{"address":address,"port":443}]}}
        self.assertEqual(d.endpoint_labels({"outbounds":[ob("example.invalid")]}),{"vpn01":["example.invalid",443]})
        self.assertEqual(d.endpoint_labels({"outbounds":[ob("secret@host")] }),{})
