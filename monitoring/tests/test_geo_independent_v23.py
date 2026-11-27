"""Offline regression for the exact staged v23 builder, no router or network."""
import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

SOURCE = Path(__file__).resolve().parents[2] / "xray/candidates/geo-independent-v23/xray-update-v23.py"
NOW = 1795790000

def outbound(i, protocol="vless"):
    return {"tag":"vpn%02d"%i,"protocol":protocol,
            "settings":{"vnext":[{"address":"fixture%d.invalid"%i,"port":443,
                                   "users":[{"id":"fixture-only"}]}]},
            "streamSettings":{"network":"tcp"}}

def converter(line, i):
    return outbound(i), "fixture"

def event(code, **changes):
    return dict({"status":"ok","route_verified":True,"checked_at":NOW,"http_code":code}, **changes)

def positive(**changes):
    return dict({"internet":event(204),"openai":event(401),
                 "exit_ip":{"status":"timeout"},"geo":{"status":"geo_unavailable"}}, **changes)

def load():
    spec = importlib.util.spec_from_file_location("geo_v23_candidate", SOURCE)
    mod = importlib.util.module_from_spec(spec)
    fake = types.ModuleType("setup_xray")
    fake.create_outbound = converter
    with patch.dict(sys.modules, {"setup_xray":fake}), patch.object(sys,"path",list(sys.path)):
        spec.loader.exec_module(mod)
    return mod

class QualificationTests(unittest.TestCase):
    def setUp(self):
        self.m = load()
        self.out = io.StringIO()
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(contextlib.redirect_stdout(self.out))

    def select(self, results, converter_fn=converter, deadline=800):
        return self.m.select_pool(["fixture"]*len(results),deadline=deadline,
                    converter=converter_fn,probe=Mock(side_effect=results),
                    clock=lambda:NOW,monotonic=lambda:0)

    def test_vpn04_geo_timeout_admitted(self):
        results=[positive(),{},positive(),positive(geo={"status":"timeout"})]
        allowed,bad=self.select(results)
        self.assertEqual([x["tag"] for x in allowed],["vpn01","vpn03","vpn04"])
        self.assertEqual(bad,["vpn02"])
        self.assertIn("vpn04 ALLOWED internet=ok openai=ok exit_ip=timeout geo=timeout",self.out.getvalue())

    def test_optional_probes_never_gate(self):
        for optional in ({},None,{"status":"network_error"},{"status":"invalid_response"},
                         {"status":"ok","ip":"203.0.113.1","country":"DE"}):
            self.assertTrue(self.m.qualify(positive(exit_ip=optional,geo=optional),NOW))
        self.assertTrue(self.m.qualify({"internet":event(204),"openai":event(401)},NOW))

    def test_no_ip_or_geo_can_bypass_mandatory(self):
        for kind,code in (("internet",204),("openai",401)):
            for bad in (None,{},event(code,status="timeout"),event(code,route_verified=False),
                        event(code,route_verified=1),event(code,http_code=403),event(code,http_code=str(code)),
                        event(code,checked_at=NOW-121),event(code,checked_at=NOW+1),
                        event(code,checked_at=True)):
                result=positive(exit_ip={"status":"ok"},geo={"status":"ok"})
                result[kind]=bad
                self.assertFalse(self.m.qualify(result,NOW))
        self.assertFalse(self.m.qualify(None,NOW))

    def test_http_status_exact(self):
        for kind,code in (("internet",204),("openai",401)):
            good=Mock(returncode=0,stdout=str(code).encode())
            self.assertEqual(self.m.classify(kind,good),{"status":"ok","http_code":code})
            for wrong in (b"200",b"302",b"403",b"429",b"000"):
                self.assertEqual(self.m.classify(kind,Mock(returncode=0,stdout=wrong))["status"],"http_error")
            self.assertEqual(self.m.classify(kind,Mock(returncode=28,stdout=good.stdout))["status"],"timeout")

    def test_owner_lost_invalidates_positive(self):
        with patch.object(self.m,"live_owner",side_effect=[True,False]), patch.object(self.m,"request",return_value=Mock(returncode=0,stdout=b"401")):
            obs=self.m.observe(Mock(),12345,"openai")
        self.assertFalse(obs["route_verified"])
        self.assertEqual(obs["status"],"unknown")

    def test_real_loopback_inode(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1",0))
            port=sock.getsockname()[1]
            self.assertFalse(self.m.owned_listener(os.getpid(),port))
            sock.listen()
            self.assertTrue(self.m.owned_listener(os.getpid(),port))
            self.assertFalse(self.m.owned_listener(99999999,port))
        self.assertFalse(self.m.owned_listener(os.getpid(),port))

    def test_probe_config_and_curl(self):
        cfg=self.m.config_for(outbound(4),12345)
        self.assertEqual(cfg["inbounds"][0]["listen"],"127.0.0.1")
        self.assertEqual([x["protocol"] for x in cfg["outbounds"]],["blackhole","vless"])
        self.assertEqual(cfg["routing"]["rules"][0]["outboundTag"],"probe-out")
        with patch.object(self.m.subprocess,"run") as run:
            self.m.request(12345,"openai")
            args,kw=run.call_args
            self.assertEqual(args[0][1],"-q")
            self.assertIn("socks5h://127.0.0.1:12345",args[0])
            self.assertNotIn("--insecure",args[0])
            self.assertNotIn("--location",args[0])
            self.assertFalse(any(k.lower() in ("http_proxy","https_proxy","all_proxy","no_proxy") for k in kw["env"]))

    def test_cleanup_abort_entire_generation(self):
        with self.assertRaises(self.m.CleanupError):
            self.select([positive(),self.m.CleanupError("fixture"),positive()])

    def test_budget_and_invalid_outbound(self):
        with self.assertRaises(RuntimeError):
            self.select([positive()],deadline=94)
        def chained(line,i):
            o=outbound(i);o["proxySettings"]={"tag":"unverified"}
            return o,"fixture"
        allowed,bad=self.select([positive()],converter_fn=chained)
        self.assertEqual(allowed,[])
        self.assertEqual(bad,["vpn01"])
        self.assertFalse(self.m.valid_vless(outbound(1,"freedom"),"vpn01"))

    def invoke(self, td, results, *, test_rc=0, current=None, output=None):
        config_path=Path(td)/"config.json"
        config=current if current is not None else {
            "inbounds":[{"tag":"local-socks"},{"tag":"tproxy-in"}],
            "outbounds":[outbound(9),{"tag":"direct","protocol":"freedom"},{"tag":"blocked","protocol":"blackhole"}],
            "routing":{"domainStrategy":"AsIs"}}
        before=json.dumps(config).encode()
        config_path.write_bytes(before)
        dest=output if output is not None else Path(td)/"candidate.json"
        with patch.object(self.m,"CONFIG",config_path), patch.object(self.m,"subscription",return_value=["fixture"]*len(results)), patch.object(self.m,"probe_node",side_effect=results), patch.object(self.m.subprocess,"run",return_value=Mock(returncode=test_rc)) as run, patch.object(sys,"argv",[str(SOURCE),"--output",str(dest)]):
            # Real timestamps for the main invocation; no network or Xray exec.
            for result in results:
                if isinstance(result,dict):
                    for key in ("internet","openai"):
                        if isinstance(result.get(key),dict):
                            result[key]["checked_at"]=int(self.m.time.time())
            try:
                self.m.main()
            finally:
                self.assertEqual(config_path.read_bytes(),before)
        return dest,run

    def test_main_candidate_preserves_routing_and_no_direct(self):
        with tempfile.TemporaryDirectory() as td:
            dest,run=self.invoke(td,[{},positive(),positive()])
            cfg=json.loads(dest.read_bytes())
            self.assertEqual([x["tag"] for x in cfg["outbounds"]],["vpn02","vpn03","blocked"])
            self.assertEqual(cfg["routing"]["balancers"][0]["fallbackTag"],"vpn02")
            self.assertEqual(cfg["routing"]["rules"][-1],{"type":"field","network":"tcp,udp","outboundTag":"blocked"})
            self.assertEqual(cfg["routing"]["rules"][0]["inboundTag"],["local-socks","tproxy-in"])
            self.assertEqual([x["tag"] for x in cfg["inbounds"]],["local-socks","tproxy-in"])
            self.assertEqual(dest.stat().st_mode&0o777,0o600)
            run.assert_called_once()
            self.assertEqual(run.call_args.args[0][:3],[self.m.XRAY,"run","-test"])

    def test_main_empty_or_validation_failure_never_exports(self):
        for results,rc in (([{}],0),([positive()],1),([positive(),self.m.CleanupError("fixture")],0)):
            with tempfile.TemporaryDirectory() as td:
                with self.assertRaises(RuntimeError):
                    self.invoke(td,results,test_rc=rc)
                self.assertFalse((Path(td)/"candidate.json").exists())

    def test_output_collision_and_symlink(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"existing"
            p.write_bytes(b"untouched")
            symlink=Path(td)/"link";symlink.symlink_to(p)
            for path in (p,symlink):
                with self.assertRaises(FileExistsError):
                    self.m.write_candidate(path,b"candidate")
                self.assertEqual(p.read_bytes(),b"untouched")

    def test_non_vless_matching_selector_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            config={"outbounds":[{"tag":"vpn-untrusted","protocol":"socks"}]}
            with self.assertRaises(RuntimeError):
                self.invoke(td,[positive()],current=config)
            self.assertFalse((Path(td)/"candidate.json").exists())

    def test_log_never_emits_optional_raw_data(self):
        self.select([positive(exit_ip={"status":"ok","ip":"203.0.113.1"},
                              geo={"status":"ok","city":"PRIVATE_FIXTURE"})])
        self.assertNotIn("203.0.113.1",self.out.getvalue())
        self.assertNotIn("PRIVATE_FIXTURE",self.out.getvalue())
