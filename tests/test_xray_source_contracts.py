#!/usr/bin/env python3
"""Offline source-contract regression checks for the frozen production snapshot.

Run from a checkout: python3 -m unittest discover -s tests -p 'test_xray_source_contracts.py'
Never invokes router commands, Xray, curl, iptables, network, or live configs.
These are static contracts, NOT integration or fault-injection tests.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "xray/production/opt/bin"


def source(name):
    return (ROOT / name).read_text(encoding="utf-8")


class XraySourceContracts(unittest.TestCase):
    def test_hourly_stages_only(self):
        s = source("xray-safe-hourly.sh")
        self.assertIn('CANDIDATE="$WORK/candidate.json"', s)
        self.assertIn('"$XRAY" run -test -config "$CANDIDATE"', s)
        self.assertIn('mv -f "$WORK/staged.json" "$PENDING"', s)
        self.assertNotIn('"$SERVICE" restart', s)
        self.assertNotIn('killall xray', s)

    def test_subscription_requires_https_and_private_permissions(self):
        s = source("xray-update-v23.py")
        self.assertIn("URLFILE.stat().st_mode & 0o077", s)
        self.assertIn("url.startswith('https://')", s)
        self.assertIn("'--max-time', '60'", s)

    def test_no_eligible_server_does_not_produce_candidate(self):
        s = source("xray-update-v23.py")
        self.assertLess(s.index("if not allowed:"), s.index("candidate = copy.deepcopy(current)"))
        self.assertIn("raise RuntimeError('empty candidate pool')", s)

    def test_fallback_is_first_allowed_server(self):
        s = source("xray-update-v23.py")
        self.assertIn("first_tag = allowed[0]['tag']", s)
        self.assertIn("'fallbackTag': first_tag", s)
        self.assertIn("assert first_tag in {x['tag'] for x in allowed}", s)

    def test_outbound_selection_requires_openai(self):
        s = source("xray-update-v23.py")
        self.assertIn("api_status = check_openai(outbound)", s)
        self.assertIn("if api_status == 'reachable':", s)
        self.assertIn("allowed.append(outbound)", s)

    def test_probe_uses_isolated_local_xray_and_cleanup(self):
        s = source("xray_server_check.py")
        self.assertIn('"listen": "127.0.0.1"', s)
        self.assertIn('proc.terminate()', s)
        self.assertIn('proc.wait(timeout=3)', s)

    def test_openai_probe_accepts_unauthenticated_401(self):
        s = source("xray_openai_probe.py")
        self.assertIn("result.stdout.strip() == '401'", s)
        self.assertIn("process.terminate()", s)

    def test_watchdog_restart_trigger_and_service(self):
        s = source("xray-watchdog.sh")
        self.assertIn('SERVICE=/opt/etc/init.d/S97xray', s)
        self.assertIn('if ! port_ready; then', s)
        self.assertIn('"$SERVICE" restart', s)

    def test_home_kill_switch_has_drop(self):
        s = source("xray-ks-home.sh")
        self.assertIn('CHAIN=XRAY_KS_HOME', s)
        self.assertIn('-j DROP', s)
        self.assertIn('FORWARD', s)

    def test_wifi_rules_use_tcp_udp_tproxy(self):
        s = source("xray-wifi-rules.sh")
        self.assertIn('for proto in tcp udp', s)
        self.assertIn('--on-port 12345', s)
        self.assertIn('lookup 100', s)

    def test_known_limitations_are_explicit(self):
        self.assertNotIn('api.openai.com', source("xray-watchdog.sh"))
        self.assertIn('killall xray', (ROOT.parent / "etc/init.d/S97xray").read_text())
        self.assertIn("'protocol':'freedom'", source("setup_xray.py"))


if __name__ == "__main__":
    unittest.main()
