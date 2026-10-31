#!/usr/bin/env python3
"""Staging-only prototype of ONE cooperative S97/watchdog/S98 broker.

Do not place over production init scripts without a separate exact-file
approval and real MIPS kernel/pidfd/iptables test. State and locking are
root-only. This code deliberately refuses unknown/mismatched process owners.
"""
import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

try:
    from v30_supervisor_core import (
        FenceError, Identity, atomic_journal, gated_spawn, proc_identity,
        proc_stat, scoped_signal, supervisor_lock,
    )
except ImportError:
    from xray.staging.v30_supervisor_core import (
        FenceError, Identity, atomic_journal, gated_spawn, proc_identity,
        proc_stat, scoped_signal, supervisor_lock,
    )


class RouterPaths:
    # Source archive is immutable; these paths are activated ONLY by a
    # separately approved install, not by GitHub CI.
    run = Path("/opt/var/run")
    lock = run / "xray-v30-supervisor.lock"
    identity = run / "xray-v30-supervisor.json"
    prepared = run / "xray-v30-supervisor-prepared.json"
    xray = Path("/opt/sbin/xray")
    config = Path("/opt/etc/xray/config.json")


class Broker:
    def __init__(self, paths=None, *, run=None, probe=None):
        self.p = paths or RouterPaths()
        self.run = run or self._run
        self.probe = probe or self._tcp_ready

    @staticmethod
    def _run(args):
        return subprocess.run(args, check=True, text=True,
                              capture_output=True, timeout=20).stdout

    @staticmethod
    def _tcp_ready(port=10808):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                return True
        except OSError:
            return False

    def _expected_argv(self):
        return (str(self.p.xray), "run", "-config", str(self.p.config))

    def _valid_binary_and_cmd(self, identity):
        return (identity.exe == str(self.p.xray.resolve(strict=True))
                and identity.argv == self._expected_argv())

    def _load(self):
        if self.p.identity.is_symlink() or not self.p.identity.exists():
            raise FenceError("missing/private identity journal")
        data = json.loads(self.p.identity.read_text(encoding="utf-8"))
        if data.get("schema") != 1 or data.get("phase") not in ("active", "stopped"):
            raise FenceError("unexpected supervisor journal")
        obj = data.get("identity")
        if not isinstance(obj, dict):
            raise FenceError("missing identity")
        identity = Identity(obj["pid"], obj["start_ticks"], obj["exe"], tuple(obj["argv"]))
        if not self._valid_binary_and_cmd(identity):
            raise FenceError("untrusted journal binary or argv")
        return data, identity

    def _all_xray(self):
        found = []
        exe = self.p.xray.resolve(strict=True)
        for item in Path("/proc").iterdir():
            if not item.name.isdigit():
                continue
            try:
                if (item / "exe").resolve(strict=True) == exe:
                    found.append(int(item.name))
            except (OSError, RuntimeError):
                continue
        return sorted(found)

    def bootstrap(self, pid, start_ticks):
        """One-time non-disruptive bind to EXISTING trusted Xray identity."""
        with supervisor_lock(self.p.lock):
            if self.p.identity.exists():
                raise FenceError("already initialized")
            identity = proc_identity(pid)
            if identity.start_ticks != start_ticks or not self._valid_binary_and_cmd(identity):
                raise FenceError("bootstrap identity not equal to known production")
            if self._all_xray() != [pid] or not self.probe():
                raise FenceError("bootstrap exclusive Xray+SOCKS unproven")
            atomic_journal(self.p.identity, {
                "schema": 1, "phase": "active", "identity": asdict(identity)})
            return "BOUND_EXACT_LEGACY"

    def _verified_active(self):
        data, old = self._load()
        if data["phase"] != "active":
            raise FenceError("service not active")
        current = proc_identity(old.pid)
        if current != old or not self._valid_binary_and_cmd(current):
            raise FenceError("Xray PID/start_ticks/exe/cmdline drift")
        if self._all_xray() != [old.pid]:
            raise FenceError("unknown additional Xray process")
        return data, old

    def _stop_under_lock(self):
        state, old = self._verified_active()
        scoped_signal(old, signal.SIGTERM)
        until = time.monotonic() + 8
        while time.monotonic() < until:
            try:
                current = proc_identity(old.pid)
            except FenceError:
                break
            if current.start_ticks != old.start_ticks:
                break
            time.sleep(0.05)
        else:
            raise FenceError("old exact Xray did not exit; no SIGKILL")
        if self._all_xray() or self.probe():
            raise FenceError("unknown listener/process remains")
        atomic_journal(self.p.identity,
                       {**state, "phase": "stopped"})
        return "EXACT_XRAY_STOPPED"

    def _start_under_lock(self):
        data, old = self._load()
        if data["phase"] == "active":
            _, actual = self._verified_active()
            if not self.probe():
                raise FenceError("active Xray has no SOCKS; call restart")
            return "ALREADY_RUNNING"
        if self._all_xray() or self.probe():
            raise FenceError("unknown Xray/listener: no start")
        cmd = list(self._expected_argv())
        pid, ticks = gated_spawn(cmd[0], cmd, self.p.prepared)
        until = time.monotonic() + 10
        while time.monotonic() < until:
            try:
                new = proc_identity(pid)
                if new.start_ticks == ticks and self._valid_binary_and_cmd(new) and self.probe():
                    break
            except FenceError:
                pass
            time.sleep(0.1)
        else:
            raise FenceError("new scoped Xray readiness failed")
        if self._all_xray() != [pid]:
            raise FenceError("unexpected Xray during start")
        atomic_journal(self.p.identity, {
            "schema": 1, "phase": "active", "identity": asdict(new)})
        return "EXACT_XRAY_STARTED"

    def control(self, op):
        """All S97 and watchdog operations share this single lock inode."""
        if op not in ("start", "stop", "restart", "watchdog-once"):
            raise FenceError("unsupported controller op")
        with supervisor_lock(self.p.lock):
            if op == "stop":
                return self._stop_under_lock()
            if op == "start":
                return self._start_under_lock()
            if op == "restart":
                self._stop_under_lock()
                return self._start_under_lock()
            data, old = self._load()
            if data["phase"] == "active":
                try:
                    self._verified_active()
                except FenceError:
                    # Refuse to touch an unknown candidate or reused PID.
                    if self._all_xray() or self.probe():
                        raise
                    # Clearly dead legacy, not PID reuse/competing Xray.
                    atomic_journal(self.p.identity,
                                   {**data, "phase": "stopped"})
                    return self._start_under_lock()
                if self.probe():
                    return "HEALTHY_EXACT_XRAY"
                return self.control_restart_under_lock()
            if self._all_xray() or self.probe():
                raise FenceError("stopped state but unknown Xray/port")
            return self._start_under_lock()

    def control_restart_under_lock(self):
        self._stop_under_lock()
        return self._start_under_lock()

    def _wifi_check_under_lock(self):
        """Read-only TCP/UDP TPROXY and table-100 gate. No direct fallback."""
        try:
            rules = self.run(["/opt/sbin/iptables", "-t", "mangle", "-S", "XRAY_WIFI"])
            route = self.run(["ip", "route", "show", "table", "100"])
            return (all(("-p " + proto) in rules and
                        "--on-port 12345" in rules for proto in ("tcp", "udp"))
                    and "local default dev lo" in route)
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False

    def wifi_once(self):
        """Wifi actor's repair holds the SAME lock used by S97 and cutover.

        The existing old wifi-rules.sh can independently mutate the kernel;
        release gate remains closed until every entrypoint is replaced.
        """
        with supervisor_lock(self.p.lock):
            if self._wifi_check_under_lock():
                return "WIFI_TPROXY_HEALTHY"
            raise FenceError("WIFI_REPAIR_NOT_YET_MIGRATED_TO_BROKER")

    def loop(self, op, seconds):
        if op not in ("watchdog-once", "wifi-once"):
            raise FenceError("unknown loop")
        while True:
            try:
                if op == "watchdog-once":
                    self.control(op)
                else:
                    self.wifi_once()
            except FenceError:
                # Fail-closed: record via service manager/syslog when deployed.
                # NEVER attempt an unguarded global kill or firewall rewrite.
                print("SUPERVISOR_FENCE_BLOCKED", file=sys.stderr, flush=True)
            time.sleep(seconds)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("op", choices=("bootstrap", "start", "stop", "restart",
        "watchdog-once", "watchdog-loop", "wifi-once", "wifi-loop"))
    p.add_argument("--expected-pid", type=int)
    p.add_argument("--expected-ticks", type=int)
    a = p.parse_args()
    if os.geteuid() != 0:
        raise FenceError("root only")
    b = Broker()
    if a.op == "bootstrap":
        if a.expected_pid is None or a.expected_ticks is None:
            raise FenceError("explicit PID and ticks required")
        print(b.bootstrap(a.expected_pid, a.expected_ticks))
    elif a.op == "watchdog-loop":
        b.loop("watchdog-once", 30)
    elif a.op == "wifi-loop":
        b.loop("wifi-once", 60)
    elif a.op == "wifi-once":
        print(b.wifi_once())
    else:
        print(b.control(a.op))


if __name__ == "__main__":
    main()
