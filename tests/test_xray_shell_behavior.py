#!/usr/bin/env python3
"""Offline shell behavior tests using rewritten temporary copies and fake commands.

No production script is run at its real path; all paths point into a temp tree.
"""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "xray/production/opt/bin"


class StagingBehavior(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.etc = self.root / "etc"
        self.etc.mkdir()
        self.log = self.root / "update.log"
        self.active = self.etc / "config.json"
        self.pending = self.etc / "config.pending.json"
        self.active.write_text("ACTIVE\n")
        self.candidate = "CANDIDATE\n"
        self.updater_exit = 0
        self.xray_exit = 0

    def fake(self, name, script):
        p = self.bin / name
        p.write_text("#!/bin/sh\n" + script + "\n")
        p.chmod(0o700)
        return p

    def execute(self):
        updater = self.fake("updater.sh",
            'if [ "$FAKE_UPDATER_EXIT" -ne 0 ]; then exit "$FAKE_UPDATER_EXIT"; fi\n'
            'printf "%s" "$FAKE_CANDIDATE" > "$2"')
        xray = self.fake("xray.sh", 'exit "$FAKE_XRAY_EXIT"')
        source = (SOURCE / "xray-safe-hourly.sh").read_text()
        source = source.replace("PATH=/opt/bin:/opt/sbin:/usr/bin:/usr/sbin:/bin:/sbin",
                                "PATH=/usr/bin:/bin")
        source = source.replace("LOG=/opt/var/log/xray-update.log", f"LOG={self.log}")
        source = source.replace("CONF=/opt/etc/xray/config.json", f"CONF={self.active}")
        source = source.replace("PENDING=/opt/etc/xray/config.pending.json", f"PENDING={self.pending}")
        source = source.replace("UPDATER=/opt/bin/xray-update-v23.py", f"UPDATER={updater}")
        source = source.replace("XRAY=/opt/sbin/xray", f"XRAY={xray}")
        source = source.replace("mkdir -p /opt/var/log", f"mkdir -p {self.root}")
        source = source.replace("mktemp -d /opt/etc/xray/.update.XXXXXX",
                                f"mktemp -d {self.etc}/.update.XXXXXX")
        source = source.replace('/opt/bin/python3 "$UPDATER"', '"$UPDATER"')
        p = self.root / "safe-hourly.sh"
        p.write_text(source)
        env = {**os.environ, "FAKE_UPDATER_EXIT": str(self.updater_exit),
               "FAKE_XRAY_EXIT": str(self.xray_exit),
               "FAKE_CANDIDATE": self.candidate}
        return subprocess.run(["/bin/sh", str(p)], cwd=self.root,
                              env=env, capture_output=True, text=True, timeout=10)

    def test_stages_candidate_without_touching_active(self):
        result = self.execute()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.active.read_text(), "ACTIVE\n")
        self.assertEqual(self.pending.read_text(), self.candidate)
        self.assertIn("STAGED_ONLY", self.log.read_text())

    def test_updater_failure_preserves_active_and_pending(self):
        self.pending.write_text("OLD_PENDING\n")
        self.updater_exit = 2
        self.assertNotEqual(self.execute().returncode, 0)
        self.assertEqual(self.active.read_text(), "ACTIVE\n")
        self.assertEqual(self.pending.read_text(), "OLD_PENDING\n")

    def test_validation_failure_preserves_active_and_pending(self):
        self.pending.write_text("OLD_PENDING\n")
        self.xray_exit = 1
        self.assertNotEqual(self.execute().returncode, 0)
        self.assertEqual(self.active.read_text(), "ACTIVE\n")
        self.assertEqual(self.pending.read_text(), "OLD_PENDING\n")

    def test_same_as_active_clears_stale_pending(self):
        self.candidate = "ACTIVE\n"
        self.pending.write_text("STALE\n")
        self.assertEqual(self.execute().returncode, 0)
        self.assertFalse(self.pending.exists())
        self.assertEqual(self.active.read_text(), "ACTIVE\n")

    def test_same_as_pending_keeps_pending(self):
        self.pending.write_text(self.candidate)
        self.assertEqual(self.execute().returncode, 0)
        self.assertEqual(self.pending.read_text(), self.candidate)
        self.assertIn("PENDING_UNCHANGED", self.log.read_text())


class WatchdogBehavior(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.restart_log = self.root / "restart.log"

    def execute(self, port_ready):
        fake_netstat = self.bin / "netstat"
        fake_netstat.write_text("#!/bin/sh\n" + (
            'printf "tcp 0 0 127.0.0.1:10808 0.0.0.0:* LISTEN\\n"\n'
            if port_ready else 'exit 0\n'))
        fake_netstat.chmod(0o700)
        service = self.bin / "service"
        service.write_text('#!/bin/sh' + chr(10) + 'echo restart >> "$RESTART_LOG"' + chr(10))
        service.chmod(0o700)
        script = (SOURCE / "xray-watchdog.sh").read_text()
        script = script.replace("LOG=/opt/tmp/xray-watchdog.log",
                                f"LOG={self.root}/watchdog.log")
        script = script.replace("SERVICE=/opt/etc/init.d/S97xray", f"SERVICE={service}")
        script = script.replace("    sleep 30\ndone", "    break\ndone")
        script = script.replace("            sleep 5", "            :")
        p = self.root / "watchdog.sh"
        p.write_text(script)
        env = {**os.environ, "PATH": f"{self.bin}:/usr/bin:/bin",
               "RESTART_LOG": str(self.restart_log)}
        return subprocess.run(["/bin/sh", str(p)], env=env,
                              capture_output=True, text=True, timeout=10)

    def test_healthy_listener_no_restart(self):
        self.assertEqual(self.execute(True).returncode, 0)
        self.assertFalse(self.restart_log.exists())

    def test_missing_listener_requests_restart(self):
        self.assertEqual(self.execute(False).returncode, 0)
        self.assertEqual(self.restart_log.read_text(), "restart\n")


if __name__ == "__main__":
    unittest.main()
