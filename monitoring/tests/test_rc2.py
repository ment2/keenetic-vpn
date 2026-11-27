import json
import time
import unittest
from unittest.mock import Mock,patch
from monitoring import rc2_probe as p,rc2_snapshot as s,rc2_history as h,rc2_cycle as c
from monitoring.vpn_inventory import inventory

NOW=1795788000
def outbound(tag="vpn01",host="one.example.invalid",uuid="fixture"):
    return {"tag":tag,"protocol":"vless","settings":{"vnext":[{"address":host,"port":443,"users":[{"id":uuid}]}]},"streamSettings":{"network":"tcp"}}
def config(*outbounds):
    return {"outbounds":list(outbounds)}
def event(status="ok",ip=None,country=None,city=None,stamp=NOW,verified=True):
    return {"status":status,"checked_at":stamp,"duration_ms":42,"route_verified":verified,"ip":ip,"country":country,"city":city}
def sample():
    return {"internet":event(),"openai":event(),"exit_ip":event(ip="203.0.113.1"),"geo":event(ip="203.0.113.1",country="DE",city="Frankfurt")}
def row(cfg,obs,old=None,now=NOW,active=None):
    e=inventory(cfg); node=e[0]["node_id"]
    cache=s.update_cache(cfg,e,{node:obs},old or {},now)
    return s.snapshot(cfg,e,active,{},cache,now)["rows"][0],cache

class ProbeTests(unittest.TestCase):
    def test_exact_status_codes(self):
        for kind,good in (("internet",b"204"),("openai",b"401")):
            self.assertEqual(p.classify(kind,Mock(returncode=0,stdout=good))["status"],"ok")
            for bad in (b"200",b"403",b"429",b"000"):
                self.assertEqual(p.classify(kind,Mock(returncode=0,stdout=bad))["status"],"http_error")
    def test_geo_independent_city_optional(self):
        res=Mock(returncode=0,stdout=json.dumps({"success":True,"ip":"203.0.113.1","country_code":"DE","city":"Frankfurt"}).encode())
        self.assertEqual(p.classify("geo",res)["city"],"Frankfurt")
        self.assertIsNone(p.city_value("<script>"))
        res.stdout=b'{"success":false,"ip":"203.0.113.1"}'
        self.assertEqual(p.classify("geo",res)["status"],"geo_unavailable")
    def test_ip_no_geo(self):
        self.assertEqual(p.classify("exit_ip",Mock(returncode=0,stdout=b'{"ip":"2001:db8::1"}'))["ip"],"2001:db8::1")
    def test_owner_lost_invalidates_positive(self):
        with patch.object(p,"live_owner",side_effect=[True,False]),patch.object(p,"request",return_value=Mock(returncode=0,stdout=b"204")):
            r=p.observe(Mock(),12345,"internet")
            self.assertEqual(r["status"],"unknown")
            self.assertFalse(r["route_verified"])
    def test_explicit_proxy_no_config(self):
        with patch.object(p.subprocess,"run") as run:
            p.request(12345,"internet")
            args=run.call_args.args[0]
            self.assertEqual(args[1],"-q")
            self.assertIn("socks5h://127.0.0.1:12345",args)
            self.assertNotIn("--location",args)
    def test_budget_and_cleanup(self):
        cfg=config(outbound())
        probe=Mock(side_effect=p.CleanupError())
        self.assertEqual(p.collect(cfg,inventory(cfg),deadline=time.monotonic()+1,probe=probe),{})
        with self.assertRaises(p.CleanupError):
            p.collect(cfg,inventory(cfg),deadline=time.monotonic()+100,probe=probe)

class SnapshotTests(unittest.TestCase):
    def test_geo_failure_does_not_make_vpn_red(self):
        cfg=config(outbound()); obs=sample(); obs["geo"]=event("geo_unavailable")
        r,_=row(cfg,obs)
        self.assertEqual((r["vpn"]["status"],r["internet"]["status"],r["openai"]["status"],r["geo"]["status"]),("ok","ok","ok","geo_unavailable"))
        self.assertEqual(r["exit_ip"],"203.0.113.1")
        self.assertEqual(r["host"],"one.example.invalid")
    def test_openai_alone_confirms_vpn(self):
        cfg=config(outbound()); r,_=row(cfg,{"openai":event()})
        self.assertEqual(r["vpn"]["status"],"ok")
        self.assertEqual(r["internet"]["status"],"missing")
    def test_no_positive_not_confirmed(self):
        r,_=row(config(outbound()),{"internet":event("timeout")})
        self.assertEqual(r["vpn"]["status"],"not_confirmed")
    def test_last_geo_on_failure_and_ip_change(self):
        cfg=config(outbound()); _,cache=row(cfg,sample())
        r,_=row(cfg,{"internet":event(),"exit_ip":event(ip="203.0.113.1"),"geo":event("network_error")},cache)
        self.assertEqual(r["last_geo"]["city"],"Frankfurt")
        r,_=row(cfg,{"exit_ip":event(ip="203.0.113.2")},cache)
        self.assertIsNone(r["last_geo"])
    def test_geo_mismatching_ip(self):
        obs=sample(); obs["geo"]=event(ip="203.0.113.2",country="US",city="New York")
        r,_=row(config(outbound()),obs)
        self.assertEqual(r["geo"]["status"],"ip_mismatch")
        self.assertIsNone(r["last_geo"])
    def test_geo_can_witness_ip(self):
        obs=sample(); obs.pop("exit_ip")
        r,_=row(config(outbound()),obs)
        self.assertEqual(r["exit_ip_source"],"geo")
        self.assertEqual(r["exit_ip"],"203.0.113.1")
    def test_old_credential_generation_not_reused(self):
        cfg=config(outbound()); _,cache=row(cfg,sample())
        changed=config(outbound(uuid="changed"))
        self.assertEqual(inventory(cfg)[0]["node_id"],inventory(changed)[0]["node_id"])
        r=s.snapshot(changed,inventory(changed),{inventory(cfg)[0]["node_id"]:s.generation(cfg["outbounds"][0])},{},cache,NOW)["rows"][0]
        self.assertEqual(r["vpn"]["status"],"missing")
        self.assertTrue(r["active"])
        self.assertFalse(r["active_config_matches"])
        self.assertIsNone(r["last_geo"])
    def test_reused_tag_new_address(self):
        cfg=config(outbound()); _,cache=row(cfg,sample())
        changed=config(outbound(host="two.example.invalid"))
        r=s.snapshot(changed,inventory(changed),{},None,cache,NOW)["rows"][0]
        self.assertEqual(r["host"],"two.example.invalid")
        self.assertEqual(r["internet"]["status"],"missing")
        self.assertIsNone(r["pending"])
    def test_stale_and_future(self):
        for stamp in (NOW-1801,NOW+1):
            self.assertEqual(s.clean_obs(event(stamp=stamp),"internet",NOW)["status"],"stale")
        self.assertEqual(s.clean_obs(event(verified=False),"internet",NOW)["status"],"unknown")
    def test_payload_capacity_and_no_credentials(self):
        cfg=config(*[outbound("vpn%02d"%i,("a"*60+".")*3+"example%d.invalid"%i) for i in range(1,25)])
        e=inventory(cfg); raw={v["node_id"]:sample() for v in e}
        cache=s.update_cache(cfg,e,raw,{},NOW)
        result=s.snapshot(cfg,e,{}, {},cache,NOW)
        self.assertEqual(result["count"],24)
        self.assertNotIn("fixture",json.dumps(result))
        self.assertNotIn("generation",json.dumps(result))
    def test_history_private_fields_not_emitted(self):
        r,_=row(config(outbound()),sample())
        state=h.state_payload(r)
        self.assertNotIn("host",state)
        self.assertNotIn("exit_ip",state)
        self.assertEqual(state["geo"],"ok")
        self.assertEqual(len(list(h.messages(r["id"],r["tag"]))),6)
    def test_schedule_remap(self):
        with patch.object(c.rc1,"run_module",return_value=0) as runner:
            c.run_module("monitoring.dynamic_snapshot",["publish"])
            runner.assert_called_once_with("monitoring.rc2_snapshot",["publish"])

    def test_subscription_and_probe_coverage(self):
        cfg=config(outbound(),outbound("vpn02","two.example.invalid"))
        es=inventory(cfg); cache=s.update_cache(cfg,es,{es[0]["node_id"]:sample()}, {},NOW)
        result=s.snapshot(cfg,es,{}, {},cache,NOW,NOW-100)
        self.assertEqual(result["subscription_at"],NOW-100)
        self.assertEqual(result["probe_complete"],1)
    def test_history_does_not_resurrect_stale_positive(self):
        r,_=row(config(outbound()),sample())
        payload,expiry=h.fresh_state(r,NOW+1801)
        self.assertEqual(payload["internet"],"stale")
        self.assertEqual(payload["openai"],"stale")
        self.assertIsNone(payload["internet_ms"])
        self.assertEqual(expiry["internet"],1)
    def test_history_remaining_ttl(self):
        r,_=row(config(outbound()),sample())
        payload,expiry=h.fresh_state(r,NOW+600)
        self.assertEqual(payload["internet"],"ok")
        self.assertEqual(expiry["internet"],1200)
        msg=list(h.messages(r["id"],r["tag"],expiry))
        self.assertTrue(all(x[1]["expire_after"]==1200 for x in msg))

    def test_ten_node_unicode_payload_and_budget(self):
        # 253-character host and longest allowed non-BMP city exercise JSON escapes.
        hosts=[("a"*63+".")*3+"b"*57+("%04d"%i) for i in range(10)]
        cfg=config(*[outbound("vpn%02d"%(i+1),host) for i,host in enumerate(hosts)])
        entries=inventory(cfg)
        addr="2001:db8:ffff:ffff:ffff:ffff:ffff:ffff"
        raw={e["node_id"]:{"internet":event(),"openai":event(),"exit_ip":event(ip=addr),
                "geo":event(ip=addr,country="DE",city="𐐀"*64)} for e in entries}
        cache=s.update_cache(cfg,entries,raw,{},NOW)
        result=s.snapshot(cfg,entries,s.pool("/nonexistent"),{},cache,NOW)
        size=len(json.dumps(result,separators=(",",":"),ensure_ascii=True).encode())
        self.assertEqual(result["count"],10)
        self.assertLessEqual(size,32768)
        self.assertLessEqual(10*p.NODE_BUDGET_S,600)

    def test_history_two_phase_and_expiry_guard(self):
        r1,_=row(config(outbound()),sample())
        r2,_=row(config(outbound("vpn02","two.example.invalid")),sample())
        events=[]
        def publish(**kw):
            events.append(("discovery" if kw["retain"] else "state",kw["payload"]))
        sent=h.publish_history([r1,r2],publisher=publish,password_reader=lambda _: "test-only",
                               clock=lambda:NOW,monotonic=lambda:0,sleep=lambda x:events.append(("settle",x)))
        self.assertEqual(sent,2)
        self.assertEqual([x[0] for x in events],["discovery"]*12+["settle"]+["state"]*2)
        self.assertEqual(events[12][1],h.DISCOVERY_SETTLE_S)
        self.assertTrue(all(x[1]["expire_after"]==1800-h.EXPIRY_GUARD_S for x in events[:12]))
    def test_history_budget_before_discovery(self):
        r,_=row(config(outbound()),sample())
        pub=Mock(); sleep=Mock()
        sent=h.publish_history([r],publisher=pub,password_reader=lambda _: "test-only",
                               clock=lambda:NOW,monotonic=Mock(side_effect=[0,119]),sleep=sleep)
        self.assertEqual(sent,0)
        pub.assert_not_called()
        sleep.assert_not_called()
