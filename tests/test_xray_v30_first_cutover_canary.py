"""Safe static and mocked tests for proposed, NOT DEPLOYED trial+rollback CLI."""
import argparse
from contextlib import nullcontext
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from xray.staging import v30_first_cutover_canary as c


class ProposedCanaryContracts(unittest.TestCase):
    def test_zombie_is_not_alive(self):
        with patch.object(c, "proc_state_and_ticks", return_value=("Z", 12345)):
            self.assertIsNone(c.ticks(15329))
            self.assertFalse(c.identity_live(15329, 12345))

    def test_pid_reuse_rejected(self):
        with patch.object(c, "proc_state_and_ticks", return_value=("S", 200)):
            self.assertFalse(c.identity_live(1000, 201))
            self.assertTrue(c.identity_live(1000, 200))

    def test_watcher_must_really_be_stopped(self):
        with patch.object(c, "proc_state_and_ticks", return_value=("S", 333)):
            self.assertFalse(c.watcher_paused([3456, 333]))
        with patch.object(c, "proc_state_and_ticks", return_value=("T", 333)):
            self.assertTrue(c.watcher_paused([3456, 333]))
        with patch.object(c, "proc_state_and_ticks", return_value=("T", 334)):
            self.assertFalse(c.watcher_paused([3456, 333]))

    def test_guarded_signal_never_signals_unknown_pid(self):
        with patch.object(c, "identity_live", return_value=False), patch.object(c.os, "kill") as kill:
            with self.assertRaises(c.GateError):
                c.guarded_signal([3456, 333], c.signal.SIGTERM, "xray")
            kill.assert_not_called()

    def test_guarded_signal_requires_cmdline(self):
        with patch.object(c, "identity_live", return_value=True), patch.object(c, "command_text", return_value="other"), patch.object(c.os, "kill") as kill:
            with self.assertRaises(c.GateError):
                c.guarded_signal([3456, 333], c.signal.SIGCONT, "xray-watchdog.sh")
            kill.assert_not_called()

    def test_guarded_signal_only_exact_pid(self):
        with patch.object(c, "identity_live", return_value=True), patch.object(c, "command_text", return_value="/opt/bin/xray-watchdog.sh"), patch.object(c.os, "kill") as kill:
            c.guarded_signal([32713, 61575997], c.signal.SIGCONT, "/opt/bin/xray-watchdog.sh")
            kill.assert_called_once_with(32713, c.signal.SIGCONT)

    def test_candidate_config_is_loopback_and_keeps_old_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            old = Path(td) / "old.json"
            destination = Path(td) / "staging"
            destination.mkdir()
            cfg = {"inbounds":[{"tag":"socks"}, {"tag":"tproxy"}],
                   "outbounds":[{"tag":f"vpn{i}", "protocol":"vless"} for i in range(7)] + [{"tag":"blocked", "protocol":"blackhole"}],
                   "routing":{"rules":[]}}
            old.write_text(json.dumps(cfg))
            with patch.object(c, "ACTIVE", old), patch.object(c, "STATE_DIR", destination), patch.object(c, "XRAY", Path("/fake/xray")), patch.object(c.subprocess, "run", return_value=MagicMock(returncode=0)):
                result = c.candidate_config()
            data = json.loads(result.read_text())
            self.assertEqual(data["api"]["tag"], "v30-local-api")
            self.assertEqual(data["inbounds"][-1]["listen"], "127.0.0.1")
            self.assertEqual(data["inbounds"][-1]["port"], 19090)
            self.assertEqual(data["outbounds"], cfg["outbounds"])
            self.assertEqual(json.loads(old.read_text()), cfg)

    def test_direct_outbound_blocks_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            old = Path(td) / "old.json"
            old.write_text(json.dumps({"inbounds":[{"tag":"a"},{"tag":"b"}],
                          "outbounds":[{"protocol":"freedom"}] + [{"protocol":"vless"}]*7,
                          "routing":{}}))
            with patch.object(c, "ACTIVE", old):
                with self.assertRaises(c.GateError):
                    c.candidate_config()

    def test_kernel_tcp_udp_both_needed(self):
        def fake_call(args, timeout=15):
            if "mangle" in args: return "-A XRAY_WIFI -p tcp -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000\n-A XRAY_WIFI -p udp -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000"
            if "XRAY_KS_HOME" in args: return "-A XRAY_KS_HOME -i br0 -j DROP"
            if args == ["/opt/sbin/iptables", "-S", "FORWARD"]:
                return "-P FORWARD DROP\n-A FORWARD -j XRAY_KS_HOME"
            if args[:2] == ["ip","rule"]: return "20000: from all fwmark 0x40000000/0x40000000 lookup 100"
            if "route" in args: return "local default dev lo"
            if "ip6tables" in args[0]: return "-P FORWARD DROP"
            raise ValueError(args)
        with patch.object(c, "call", side_effect=fake_call):
            c.safe_kernel()
        def missing_udp(args, timeout=15):
            return fake_call(args,timeout).replace(" -p udp ", " -p tcp ")
        with patch.object(c, "call", side_effect=missing_udp):
            with self.assertRaises(c.GateError):
                c.safe_kernel()

    def test_first_forward_rule_is_kill_switch(self):
        def fake_call(args, timeout=15):
            if "mangle" in args:
                return ("-A XRAY_WIFI -p tcp -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000\n"
                        "-A XRAY_WIFI -p udp -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000")
            if "XRAY_KS_HOME" in args:
                return "-A XRAY_KS_HOME -i br0 -j DROP"
            if args == ["/opt/sbin/iptables", "-S", "FORWARD"]:
                return "-P FORWARD DROP\n-A FORWARD -j ACCEPT\n-A FORWARD -j XRAY_KS_HOME"
            if args[:2] == ["ip", "rule"]:
                return "20000: from all fwmark 0x40000000/0x40000000 lookup 100"
            if "route" in args:
                return "local default dev lo"
            if "ip6tables" in args[0]:
                return "-P FORWARD DROP"
            raise AssertionError(args)
        with patch.object(c, "call", side_effect=fake_call):
            with self.assertRaises(c.GateError):
                c.safe_kernel()

    def test_first_trial_explicit_network_approval_required(self):
        args = argparse.Namespace(accept_network_interruption=False)
        with patch.object(c, "preflight", side_effect=AssertionError("MUST_NOT_TOUCH_ROUTER")):
            with self.assertRaises(c.GateError):
                c.trial(args)

    def test_rollback_rejects_unknown_candidate_without_signal(self):
        state = {"phase":"candidate_running","candidate":[8000,70],
                 "old":[13546,100216734],
                 "wifi":[24097,60711544],
                 "watchdog":[32713,61575997]}
        with patch.object(c,"transaction_lock",return_value=nullcontext()), patch.object(c,"read_state",return_value=state), patch.object(c,"verify_backup"), patch.object(c,"identity_live",return_value=True), patch.object(c,"guarded_signal",side_effect=c.GateError("changed process")), patch.object(c,"state_update") as upd, patch.object(c.os,"kill") as kill:
            self.assertEqual(c.restore("test"),"blocked")
            kill.assert_not_called()
            self.assertEqual(upd.call_args.kwargs["phase"],"blocked")

    def test_guard_does_not_arm_without_journal(self):
        with patch.object(c,"read_state",return_value={"phase":"legacy"}), patch.object(c,"atomic_write") as write:
            with self.assertRaises(c.GateError):
                c.guardian()
            write.assert_not_called()

    def test_blocked_state_never_retried_automatically(self):
        state = {"phase":"blocked"}
        with patch.object(c,"transaction_lock",return_value=nullcontext()), patch.object(c,"read_state",return_value=state), patch.object(c,"verify_backup") as check:
            self.assertEqual(c.restore("deadline"), "blocked")
            check.assert_not_called()

    def test_local_manual_blocked_retry_is_identity_guarded(self):
        state = {"phase":"blocked","candidate":[8000,70],
                 "old":[13546,100216734],
                 "wifi":[24097,60711544],
                 "watchdog":[32713,61575997]}
        with patch.object(c,"transaction_lock",return_value=nullcontext()), patch.object(c,"read_state",return_value=state), patch.object(c,"verify_backup"), patch.object(c,"identity_live",return_value=True), patch.object(c,"guarded_signal",side_effect=c.GateError("identity mismatch")) as guard, patch.object(c,"state_update") as update, patch.object(c.os,"kill") as kill:
            self.assertEqual(c.restore("local_operator",allow_retry_blocked=True),"blocked")
            guard.assert_called_once()
            kill.assert_not_called()
            self.assertEqual(update.call_args.kwargs["phase"],"blocked")

    def test_successful_mock_restore_unfreezes_only_after_old_health(self):
        state = {"phase":"candidate_running","candidate":None,
                 "old":[13546,100216734], "wifi":[24097,60711544],
                 "watchdog":[32713,61575997]}
        with patch.object(c,"transaction_lock",return_value=nullcontext()), patch.object(c,"read_state",return_value=state), patch.object(c,"verify_backup"), patch.object(c,"identity_live",return_value=True), patch.object(c,"owned_xray_pids",return_value=[13546]), patch.object(c,"listeners_owned",return_value=True), patch.object(c,"socks_openai_check",return_value=True), patch.object(c,"safe_kernel") as kernel, patch.object(c,"guarded_signal") as sig, patch.object(c,"state_update"), patch.object(c,"ticks",return_value=100216734):
            self.assertEqual(c.restore("mock_success"),"restored")
            kernel.assert_called_once()
            self.assertEqual(sig.call_count,2)
            self.assertEqual(sig.call_args_list[0].args[1],c.signal.SIGCONT)
            self.assertEqual(sig.call_args_list[1].args[1],c.signal.SIGCONT)

    def test_state_fenced_only_after_two_stopped_confirmations(self):
        import inspect
        source = inspect.getsource(c.trial)
        self.assertLess(source.index('state_update(phase="fencing")'),
                        source.index("if watcher_paused(watchdog) and watcher_paused(wifi)"))
        self.assertLess(source.index("if watcher_paused(watchdog) and watcher_paused(wifi)"),
                        source.index('state_update(phase="fenced")'))

    def test_source_is_not_currently_deployed(self):
        path=Path(c.__file__).resolve()
        self.assertIn("staging",str(path))
        self.assertNotEqual(path,Path("/opt/bin/v30_first_cutover_canary.py"))


if __name__ == "__main__":
    unittest.main()
