#!/usr/bin/env python3
"""Disposable real Xray 26.2.6 MIPS32LE QEMU guardian recovery rehearsal.

Uses real qemu-mipsel -> Xray SOCKS5 TCP and UDP ASSOCIATE; loopback
echo servers only. Never binds real ingress, touches firewall or router.
The second guardian recovers if primary is killed holding the SAME flock.
NOT a production cutover or TPROXY/IPv6 leak test.
"""
import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

from xray.staging.v30_supervisor_core import (
    FenceError, atomic_journal, gated_spawn, proc_identity, proc_stat,
    scoped_signal, supervisor_lock,
)
from xray.lab.xray_v30_api_continuity import EchoBackend, free_port, socks_connect, echo
from xray.lab.xray_v30_dual_process import UdpEcho, config, udp_associate


def strict_lab(root):
    root = Path(root).resolve()
    if Path("/opt/etc/xray/config.json").exists():
        raise FenceError("PRODUCTION_NEVER")
    if not (str(root).startswith("/tmp/") or
            str(root).startswith("/home/runner/work/")):
        raise FenceError("disposable runner only")
    return root


def load(path):
    return json.loads(Path(path).read_text())


def alive(pid, ticks):
    try:
        state, _, real_ticks = proc_stat(pid)
        return state not in ("X", "Z") and real_ticks == ticks
    except FenceError:
        return False


def check(port, marker):
    try:
        with socks_connect(port) as conn:
            if echo(conn, marker) != "MIPS":
                return False
        udp_associate(port, marker.encode())
        return True
    except (OSError, AssertionError, TimeoutError, ValueError):
        return False


def wait_check(port, marker, seconds=16):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if check(port, marker):
            return True
        time.sleep(0.15)
    return False


def cmd(root, cfg):
    meta = load(root / "runtime.json")
    return [meta["qemu"], meta["mips_binary"], "run", "-config", str(root / cfg)]


def controller(root, at):
    root = strict_lab(root)
    meta = load(root / "runtime.json")
    port = meta["port"]
    with supervisor_lock(root / "shared.lock", timeout=4):
        original = load(root / "old-identity.json")
        old = proc_identity(original["pid"])
        if old.start_ticks != original["start_ticks"] or not check(port, "old"):
            raise FenceError("old Xray identity/transport drift")
        atomic_journal(root / "journal.json", {"phase": "armed",
                 "old": original, "candidate": None})
        scoped_signal(old, signal.SIGTERM)
        end = time.monotonic() + 7
        while alive(old.pid, old.start_ticks) and time.monotonic() < end:
            time.sleep(0.05)
        if alive(old.pid, old.start_ticks):
            raise FenceError("old MIPS Xray would not exit")
        atomic_journal(root / "journal.json",
                       {"phase": "legacy_stopped", "old": original, "candidate": None})
        argv = cmd(root, "candidate.json")
        pid, ticks = gated_spawn(argv[0], argv, root / "candidate-prepared.json")
        if at == "prepared":
            (root / "controller-ready").write_text("PREPARED_FSYNCED_BEFORE_COMMIT\n")
        else:
            if not wait_check(port, "candidate", 16):
                raise FenceError("candidate MIPS Xray TCP+UDP failed")
            ident = proc_identity(pid)
            if ident.start_ticks != ticks or tuple(argv) != ident.argv:
                raise FenceError("candidate identity drift")
            atomic_journal(root / "journal.json",
                           {"phase": "candidate_running",
                            "old": original, "candidate": asdict(ident)})
            (root / "controller-ready").write_text("CANDIDATE_RUNNING\n")
        while True:
            time.sleep(0.4)


def guardian(root, role):
    root = strict_lab(root)
    meta = load(root / "runtime.json")
    (root / ("guardian-" + role + "-ready")).write_text("READY\n")
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        try:
            with supervisor_lock(root / "shared.lock", timeout=0.25):
                s = load(root / "journal.json")
                if s["phase"] == "restored":
                    return
                if role == "primary":
                    (root / "primary-held-lock").write_text("HELD\n")
                    while True:
                        time.sleep(0.4)
                if s["phase"] not in ("armed", "legacy_stopped", "candidate_running"):
                    raise FenceError("unexpected journal state")
                prep = root / "candidate-prepared.json"
                if prep.exists():
                    prepared = load(prep)
                    pid, ticks = prepared["pid"], prepared["start_ticks"]
                    if alive(pid, ticks):
                        current = proc_identity(pid)
                        if current.start_ticks != ticks or current.argv != tuple(prepared["argv"]):
                            raise FenceError("candidate PID identity drift")
                        scoped_signal(current, signal.SIGTERM)
                        end = time.monotonic() + 8
                        while alive(pid, ticks) and time.monotonic() < end:
                            time.sleep(0.04)
                        if alive(pid, ticks):
                            raise FenceError("candidate did not exit")
                if check(meta["port"], "candidate"):
                    raise FenceError("unreconciled candidate SOCKS+UDP")
                # Missing candidate journal is okay ONLY when no candidate can
                # be running. Lab's generation gate records both known owners.
                argv = cmd(root, "old.json")
                pid, ticks = gated_spawn(argv[0], argv, root / "restore-prepared.json")
                if not wait_check(meta["port"], "restored", 16):
                    raise FenceError("old MIPS Xray TCP/UDP could not rebind")
                actual = proc_identity(pid)
                if actual.start_ticks != ticks:
                    raise FenceError("restored identity changed")
                atomic_journal(root / "journal.json", {
                    "phase": "restored", "old": s["old"],
                    "candidate": s.get("candidate"), "restored": asdict(actual)})
                (root / "success").write_text("MIPS_REAL_XRAY_TCP_UDP_RESTORED\n")
                return
        except FenceError as exc:
            if "lock busy" in str(exc):
                continue
            atomic_journal(root / ("guardian-" + role + "-blocked.json"),
                           {"reason": type(exc).__name__, "phase": "blocked"})
            raise
    raise FenceError("guardian timed out waiting for controller or primary")


def stop_known(pid, ticks):
    if not alive(pid, ticks):
        return
    ident = proc_identity(pid)
    if ident.start_ticks == ticks:
        scoped_signal(ident, signal.SIGTERM)


def demo(xray, root, at):
    root = strict_lab(root)
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    qemu = str(Path(xray).resolve())
    # xray is the existing QEMU wrapper; its first exec resolves to qemu-mipsel.
    version = subprocess.run([qemu, "version"], capture_output=True,
                             text=True, timeout=20, check=True).stdout
    if "26.2.6" not in version or "linux/mipsle" not in version:
        raise FenceError("not actual Xray 26.2.6 MIPSLE")
    # Wrapper is a script executing qemu-mipsel. Avoid storing shell argv
    # in gated_spawn: use actual qemu absolute path and verified binary.
    binary = os.environ.get("XRAY_MIPS_BINARY")
    if not binary:
        raise FenceError("missing pinned MIPS binary location")
    qemubin = subprocess.run(["command", "-v", "qemu-mipsel"],
                            shell=False, capture_output=True, text=True)
    # command is a shell builtin, prefer exec path resolved by shutil.
    import shutil
    qemubin = shutil.which("qemu-mipsel")
    if not qemubin or not Path(binary).is_file():
        raise FenceError("QEMU/MIPS binary not present")
    port = free_port()
    echo_server = EchoBackend("MIPS")
    udp_server = UdpEcho()
    echo_server.start()
    udp_server.start()
    old = None
    ctrl = None
    guards = []
    tracked = []
    try:
        for filename in ("old.json", "candidate.json"):
            (root / filename).write_text(json.dumps(
                config(port, echo_server.port, udp_port=udp_server.port, enable_udp=True)))
        atomic_journal(root / "runtime.json", {"qemu": qemubin,
               "mips_binary": str(Path(binary).resolve()), "port": port})
        argv = cmd(root, "old.json")
        old = subprocess.Popen(argv, stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True)
        oldid = proc_identity(old.pid)
        tracked.append((oldid.pid, oldid.start_ticks))
        atomic_journal(root / "old-identity.json", asdict(oldid))
        if not wait_check(port, "old", 20):
            raise FenceError("initial MIPS32LE Xray not ready on TCP+UDP")
        atomic_journal(root / "journal.json", {"phase": "legacy",
                        "old": asdict(oldid), "candidate": None})
        for role in ("primary", "secondary"):
            proc = subprocess.Popen([sys.executable, "-m",
                "xray.lab.v30_mips_guardian_failover", "--guardian",
                str(root), "--role", role], stdin=subprocess.DEVNULL,
                stdout=(root / ("guardian-" + role + ".log")).open("w"),
                stderr=subprocess.STDOUT, start_new_session=True)
            guards.append(proc)
            tracked.append((proc.pid, proc_stat(proc.pid)[2]))
        end = time.monotonic() + 5
        while not all((root / ("guardian-" + x + "-ready")).exists()
                      for x in ("primary", "secondary")):
            if time.monotonic() > end:
                raise FenceError("guardians not both ready")
            time.sleep(0.02)
        ctrl = subprocess.Popen([sys.executable, "-m",
            "xray.lab.v30_mips_guardian_failover", "--controller",
            str(root), "--crash-at", at], stdin=subprocess.DEVNULL,
            stdout=(root / "controller.log").open("w"),
            stderr=subprocess.STDOUT, start_new_session=True)
        tracked.append((ctrl.pid, proc_stat(ctrl.pid)[2]))
        end = time.monotonic() + 26
        while not (root / "controller-ready").exists():
            if ctrl.poll() is not None:
                raise FenceError("controller unexpectedly exited; see logs")
            if time.monotonic() > end:
                raise FenceError("controller never prepared cutover")
            time.sleep(0.04)
        prepared = load(root / "candidate-prepared.json")
        tracked.append((prepared["pid"], prepared["start_ticks"]))
        ctrl.kill()  # Own disposable runner process, never router
        ctrl.wait(timeout=3)
        end = time.monotonic() + 8
        while not (root / "primary-held-lock").exists():
            if time.monotonic() > end:
                raise FenceError("primary guardian never acquired same mutex")
            time.sleep(0.02)
        guards[0].kill()  # Inject crash while primary guardian holds flock
        guards[0].wait(timeout=3)
        end = time.monotonic() + 35
        while not (root / "success").exists():
            if (root / "guardian-secondary-blocked.json").exists():
                raise FenceError("secondary guardian entered blocked state")
            if time.monotonic() > end:
                raise FenceError("secondary guardian did not restore")
            time.sleep(0.05)
        state = load(root / "journal.json")
        if state["phase"] != "restored" or not check(port, "restored"):
            raise FenceError("false claim of MIPS TCP/UDP restoration")
        restored = state["restored"]
        tracked.append((restored["pid"], restored["start_ticks"]))
        print("MIPS_GUARD: PASS two real Xray 26.2.6 MIPS32LE processes via QEMU")
        print("MIPS_GUARD: PASS SOCKS5 TCP and UDP ASSOCIATE old/candidate/restore")
        print("MIPS_GUARD: PASS controller crash at " + at)
        print("MIPS_GUARD: PASS primary guardian killed holding common flock")
        print("MIPS_GUARD: PASS independent secondary restored real MIPS Xray TCP+UDP")
        print("LIMITATION: 127.0.0.1 SOCKS5 only; no production TPROXY, reboot or real VPN")
    finally:
        for filename in ("candidate-prepared.json", "restore-prepared.json"):
            f = root / filename
            if f.exists():
                d = load(f)
                tracked.append((d["pid"], d["start_ticks"]))
        for pid, ticks in reversed(tracked):
            try:
                stop_known(pid, ticks)
            except (FenceError, ProcessLookupError, OSError):
                pass
        for p in [ctrl, old, *guards]:
            if p is not None:
                try:
                    p.wait(timeout=3)
                except (subprocess.TimeoutExpired, ChildProcessError):
                    if p.poll() is None:
                        p.kill()
                        p.wait(timeout=3)
        echo_server.close()
        udp_server.close()


def main():
    p = argparse.ArgumentParser()
    m = p.add_mutually_exclusive_group(required=True)
    m.add_argument("--demo", type=Path)
    m.add_argument("--controller", type=Path)
    m.add_argument("--guardian", type=Path)
    p.add_argument("--xray")
    p.add_argument("--role", choices=("primary", "secondary"))
    p.add_argument("--crash-at", choices=("prepared", "running"), default="running")
    a = p.parse_args()
    if a.demo:
        demo(a.xray, a.demo, a.crash_at)
    elif a.controller:
        controller(a.controller, a.crash_at)
    else:
        guardian(a.guardian, a.role)


if __name__ == "__main__":
    main()
