#!/usr/bin/env python3
"""Behavioral tests for the frozen updater, with all network/router effects mocked.

Only the AST of main() is compiled. Top-level imports, real subscription, Xray,
curl, probes and router paths are never executed. Temporary files only.
"""
import ast
import contextlib
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock

UPDATER = Path(__file__).resolve().parents[1] / "xray/production/opt/bin/xray-update-v23.py"


def isolated_main():
    tree = ast.parse(UPDATER.read_text(encoding="utf-8"), filename=str(UPDATER))
    fn = next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == "main")
    ns = {"__builtins__": __builtins__}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(UPDATER), "exec"), ns)
    return ns["main"]


class UpdaterBehavior(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = self.root / "config.json"
        self.current = {
            "inbounds": [{"tag": "local-socks"}, {"tag": "tproxy-in"}],
            "outbounds": [
                {"tag": "old-vpn", "protocol": "vless"},
                {"tag": "direct", "protocol": "freedom"},
                {"tag": "old-blocked", "protocol": "blackhole"},
            ],
            "routing": {"rules": [{"outboundTag": "direct"}]},
        }
        self.config.write_text(json.dumps(self.current))
        self.out = self.root / "candidate.json"
        self.lines = ["vless://server1", "vless://server2", "vless://server3"]
        self.responses = ["reachable", "network_error", "reachable"]
        self.validation_rc = 0
        self.calls = []
        self.main = isolated_main()

    def run_updater(self, probe_status="ok", existing=False):
        if existing:
            self.out.write_text("do-not-overwrite")
        allowed_outbounds = [
            {"tag": "vpn01", "protocol": "vless"},
            {"tag": "vpn02", "protocol": "vless"},
            {"tag": "vpn03", "protocol": "vless"},
        ]
        def create_outbound(line, i):
            return copy.deepcopy(allowed_outbounds[i - 1]), "mock"
        def probe(outbound):
            if probe_status == "ok":
                return {"status": "ok", "ip": "198.51.100.1", "country_code": "ZZ"}
            return {"status": probe_status}
        def check_openai(outbound):
            self.calls.append(outbound["tag"])
            return self.responses[int(outbound["tag"][-2:]) - 1]
        def fake_run(args, **kwargs):
            self.assertEqual(args[:3], ["/opt/sbin/xray", "run", "-test"])
            self.assertEqual(args[3], "-config")
            return types.SimpleNamespace(returncode=self.validation_rc)
        ns = self.main.__globals__
        ns.update({
            "sys": types.SimpleNamespace(argv=["updater", "--output", str(self.out)]),
            "CONFIG": self.config, "subscription": lambda: self.lines,
            "create_outbound": create_outbound, "probe": probe,
            "check_openai": check_openai, "copy": copy, "json": json,
            "Path": Path, "tempfile": tempfile, "os": __import__("os"),
            "subprocess": types.SimpleNamespace(run=fake_run, DEVNULL=subprocess.DEVNULL),
            "XRAY": "/opt/sbin/xray",
        })
        with contextlib.redirect_stdout(io.StringIO()):
            self.main()

    def test_mixed_pool_fallback_and_no_direct(self):
        self.run_updater()
        candidate = json.loads(self.out.read_text())
        self.assertEqual(self.calls, ["vpn01", "vpn02", "vpn03"])
        self.assertEqual([x["tag"] for x in candidate["outbounds"]],
                         ["vpn01", "vpn03", "blocked"])
        self.assertEqual(candidate["routing"]["balancers"][0]["fallbackTag"], "vpn01")
        self.assertEqual(candidate["routing"]["balancers"][0]["strategy"]["type"], "leastPing")
        self.assertEqual(candidate["routing"]["rules"][0]["inboundTag"],
                         ["local-socks", "tproxy-in"])
        self.assertEqual(candidate["routing"]["rules"][1]["outboundTag"], "blocked")
        self.assertTrue(candidate["observatory"]["enableConcurrency"])
        self.assertEqual(json.loads(self.config.read_text()), self.current)

    def test_all_api_checks_fail_closed(self):
        self.responses = ["network_error"] * 3
        with self.assertRaisesRegex(RuntimeError, "empty candidate pool"):
            self.run_updater()
        self.assertFalse(self.out.exists())
        self.assertEqual(json.loads(self.config.read_text()), self.current)

    def test_geo_failure_skips_api_and_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "empty candidate pool"):
            self.run_updater(probe_status="network_error")
        self.assertEqual(self.calls, [])
        self.assertFalse(self.out.exists())

    def test_xray_validation_failure_no_candidate(self):
        self.validation_rc = 1
        with self.assertRaisesRegex(RuntimeError, "candidate Xray validation failed"):
            self.run_updater()
        self.assertFalse(self.out.exists())
        self.assertEqual(json.loads(self.config.read_text()), self.current)

    def test_existing_output_is_not_overwritten(self):
        with self.assertRaisesRegex(RuntimeError, "output already exists"):
            self.run_updater(existing=True)
        self.assertEqual(self.out.read_text(), "do-not-overwrite")
        self.assertEqual(json.loads(self.config.read_text()), self.current)


if __name__ == "__main__":
    unittest.main()
