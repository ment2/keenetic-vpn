"""First-migration dry-run tests: synthetic inventory, no router or network."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "xray/lab/first_migration_dry_run_v30.py"
spec = importlib.util.spec_from_file_location("first_migration_dry_run_v30", SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def good():
    return {
        "config_sha256": "a" * 64, "xray_binary_sha256": "b" * 64,
        "pid": 1234, "start_ticks": 123456,
        "socks_listener": "127.0.0.1:10808",
        "tproxy_listener": "0.0.0.0:12345",
        "watchdog_mode": "legacy-killall", "kill_switch": True,
        "tproxy_chain": True, "route_table_100": True,
        "candidate_test": True, "candidate_api": True,
        "rollback_artifact": True, "outbound_direct_count": 0,
        "outbound_block_count": 1, "subscription_staging_only": True,
        "ingress_handoff_proven": False,
    }


class DryRunTests(unittest.TestCase):
    def test_realistic_first_migration_is_blocked(self):
        r = mod.evaluate(good())
        self.assertEqual(r["decision"], "NOT_AUTHORIZED")
        self.assertIn("unproven exclusive", " ".join(r["failures"]))
        self.assertEqual(r["production_commands"], [])

    def test_abstract_all_gates_still_not_deployment_permission(self):
        d = good()
        d["ingress_handoff_proven"] = True
        r = mod.evaluate(d)
        self.assertEqual(r["decision"], "PRECHECKS_ONLY_NO_DEPLOY")
        self.assertTrue(r["required_manual_approval"])

    def test_direct_fallback_is_blocked(self):
        d = good()
        d["outbound_direct_count"] = 1
        self.assertIn("direct/freedom", " ".join(mod.evaluate(d)["failures"]))

    def test_missing_blackhole_is_blocked(self):
        d = good()
        d["outbound_block_count"] = 0
        self.assertIn("blackhole", " ".join(mod.evaluate(d)["failures"]))

    def test_watchdog_mismatch_is_blocked(self):
        d = good()
        d["watchdog_mode"] = "unknown"
        self.assertIn("watchdog_mode", " ".join(mod.evaluate(d)["failures"]))

    def test_missing_kill_switch_is_blocked(self):
        d = good()
        d["kill_switch"] = False
        self.assertIn("kill_switch", " ".join(mod.evaluate(d)["failures"]))

    def test_missing_tproxy_route_is_blocked(self):
        d = good()
        d["route_table_100"] = False
        self.assertIn("route_table_100", " ".join(mod.evaluate(d)["failures"]))

    def test_stale_process_identity_is_blocked(self):
        d = good()
        d["start_ticks"] = 0
        self.assertIn("start ticks", " ".join(mod.evaluate(d)["failures"]))

    def test_invalid_sha_is_blocked(self):
        d = good()
        d["config_sha256"] = "bad"
        self.assertIn("SHA256", " ".join(mod.evaluate(d)["failures"]))

    def test_missing_inventory_field_is_blocked(self):
        d = good()
        del d["candidate_api"]
        with self.assertRaises(mod.GateError):
            mod.evaluate(d)

    def test_no_downtime_promise(self):
        r = mod.evaluate(good())
        self.assertIn("no zero-downtime", r["outage_estimate"]["guarantee"])

    def test_cli_dry_run_does_not_modify_input(self):
        with tempfile.TemporaryDirectory() as td:
            src, out = Path(td) / "input.json", Path(td) / "report.json"
            src.write_text(json.dumps(good()))
            before = src.read_bytes()
            result = subprocess.run([sys.executable, str(SCRIPT),
                                     "--inventory", str(src), "--output", str(out)],
                                    capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(src.read_bytes(), before)
            self.assertEqual(json.loads(out.read_text())["decision"], "NOT_AUTHORIZED")


if __name__ == "__main__":
    unittest.main()
