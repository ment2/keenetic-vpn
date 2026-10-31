#!/usr/bin/env python3
"""Disposable REAL-process TCP+UDP first-cutover/guardian rehearsal.

Use only on GitHub's ephemeral runner. Explicitly rejects Entware/prod hosts.
This is not real Xray/TPROXY, and cannot authorize a router cutover.
"""
import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import select
import signal
import socket
import subprocess
import sys
import time

from xray.staging.v30_supervisor_core import (
    FenceError, Identity, atomic_journal, gated_spawn, proc_identity,
    proc_stat, scoped_signal, supervisor_lock,
)


def require_disposable(root):
    root = Path(root).resolve()
    if (Path("/opt/etc/xray/config.json").exists() or
            Path("/opt/etc/init.d/S97xray").exists() or
            not (str(root).startswith("/tmp/") or
                 str(root).startswith("/home/runner/work/"))):
        raise FenceError("DISPOSABLE_RUNNER_ONLY; no production operations")
    if root.is_symlink():
        raise FenceError("symlink root")
    return root


def read_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def identity_from_dict(obj):
    return Identity(obj["pid"], obj["start_ticks"], obj["exe"], tuple(obj["argv"]))


def is_alive(pid, tick=None):
    try:
        state, _, actual = proc_stat(pid)
        return state not in ("Z", "X") and (tick is None or actual == tick)
    except FenceError:
        return False


def allocate_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def server(role, tcp_port, udp_port):
    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcp.bind(("127.0.0.1", tcp_port))
    udp.bind(("127.0.0.1", udp_port))
    tcp.listen(8)
    try:
        while True:
            ready, _, _ = select.select((tcp, udp), (), (), 0.25)
            for sock in ready:
                if sock is tcp:
                    conn, _ = tcp.accept()
                    with conn:
                        conn.settimeout(1)
                        conn.sendall((role + "-tcp").encode())
                else:
                    data, peer = udp.recvfrom(256)
                    if data == b"ping":
                        udp.sendto((role + "-udp").encode(), peer)
    finally:
        tcp.close()
        udp.close()


def probe(tcp_port, udp_port, role):
    try:
        with socket.create_connection(("127.0.0.1", tcp_port), timeout=0.1) as sock:
            if sock.recv(64) != (role + "-tcp").encode():
                return False
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(0.15)
            sock.sendto(b"ping", ("127.0.0.1", udp_port))
            payload, _ = sock.recvfrom(64)
            return payload == (role + "-udp").encode()
    except (OSError, TimeoutError):
        return False


def await_probe(tcp_port, udp_port, role, seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if probe(tcp_port, udp_port, role):
            return True
        time.sleep(0.05)
    return False


def server_cmd(role, ports):
    return [sys.executable, "-m", "xray.lab.v30_fenced_process_recovery_lab",
            "--server", role, "--tcp", str(ports[0]), "--udp", str(ports[1])]


def cleanup_lab_pid(pid, expected_ticks):
    if not is_alive(pid, expected_ticks):
        return
    # This function is ONLY reachable from disposable --demo and only
    # for exact child identities captured by the demo itself.
    try:
        if proc_stat(pid)[2] == expected_ticks:
            os.kill(pid, signal.SIGKILL)
    except (ProcessLookupError, OSError, FenceError):
        pass


def controller(root, ports):
    root = require_disposable(root)
    lock = root / "supervisor.lock"
    journal = root / "transaction.json"
    state = read_json(journal)
    old = identity_from_dict(state["old"])
    guardian = None
    with supervisor_lock(lock, timeout=3.0):
        if not probe(*ports, "legacy"):
            raise FenceError("legacy TCP/UDP baseline missing")
        # Persist intent and a guardian independent of the controller.
        atomic_journal(journal, {**state, "phase": "armed"})
        with (root / "guardian.log").open("w") as log:
            guardian = subprocess.Popen([sys.executable, "-m",
                 "xray.lab.v30_fenced_process_recovery_lab", "--guardian",
                 str(root), "--tcp", str(ports[0]), "--udp", str(ports[1])],
                 stdin=subprocess.DEVNULL, stdout=log,
                 stderr=subprocess.STDOUT, start_new_session=True)
        atomic_journal(root / "guardian.json", {"pid": guardian.pid,
                       "ticks": proc_stat(guardian.pid)[2]})
        deadline = time.monotonic() + 3
        while not (root / "guardian-ready").exists():
            if time.monotonic() > deadline:
                raise FenceError("independent guardian never became ready")
            time.sleep(0.02)
        scoped_signal(old, signal.SIGTERM)
        deadline = time.monotonic() + 3
        while is_alive(old.pid, old.start_ticks):
            if time.monotonic() > deadline:
                raise FenceError("legacy refused targeted termination")
            time.sleep(0.03)
        atomic_journal(journal, {**state, "phase": "legacy_stopped"})
        cmd = server_cmd("candidate", ports)
        pid, start_ticks = gated_spawn(cmd[0], cmd, root / "candidate-prepared.json")
        if not await_probe(*ports, "candidate", 3):
            raise FenceError("candidate failed to own both TCP and UDP")
        candidate = proc_identity(pid)
        if candidate.start_ticks != start_ticks:
            raise FenceError("candidate PID reuse")
        atomic_journal(journal, {**state, "phase": "candidate_running",
                        "candidate": asdict(candidate)})
        (root / "cutover-ready").write_text("CANDIDATE_ON_REAL_TCP_UDP\n")
        # Simulate a hung controller, while holding the common mutex.
        # The demo kills this process; only independent guardian may recover.
        while True:
            time.sleep(0.2)


def guardian(root, ports):
    root = require_disposable(root)
    (root / "guardian-ready").write_text("GUARD_READY\n")
    # Bounded restart independent of the controller. The shared flock is
    # auto-released by the kernel when a killed controller exits.
    deadline = time.monotonic() + 9
    while time.monotonic() < deadline:
        try:
            with supervisor_lock(root / "supervisor.lock", timeout=0.3):
                state = read_json(root / "transaction.json")
                if state.get("phase") == "restored":
                    return
                if state.get("phase") not in ("armed", "legacy_stopped",
                                              "candidate_running"):
                    raise FenceError("unknown journal phase")
                if state["phase"] == "armed" and probe(*ports, "legacy"):
                    atomic_journal(root / "transaction.json",
                                   {**state, "phase": "restored"})
                    return
                candidate_record = root / "candidate-prepared.json"
                if candidate_record.exists():
                    rec = read_json(candidate_record)
                    pid, ticks = rec["pid"], rec["start_ticks"]
                    if is_alive(pid, ticks):
                        # Must prove executable and exact process identity
                        # from durable record before any signal.
                        live = proc_identity(pid)
                        if live.start_ticks != ticks or (
                                state.get("candidate") and
                                live != identity_from_dict(state["candidate"])):
                            raise FenceError("candidate identity mismatch")
                        scoped_signal(live, signal.SIGTERM)
                        finish = time.monotonic() + 3
                        while is_alive(pid, ticks) and time.monotonic() < finish:
                            time.sleep(0.03)
                        if is_alive(pid, ticks):
                            raise FenceError("candidate would not exit")
                # No unknown listener on either port; never kill strangers.
                if probe(*ports, "candidate"):
                    raise FenceError("candidate still serves sockets")
                cmd = server_cmd("legacy", ports)
                oldpid, oldticks = gated_spawn(cmd[0], cmd,
                                   root / "restored-prepared.json")
                if not await_probe(*ports, "legacy", 3):
                    raise FenceError("TCP/UDP legacy recovery failed")
                atomic_journal(root / "transaction.json",
                               {**state, "phase": "restored",
                                "restored": {"pid": oldpid,
                                             "start_ticks": oldticks}})
                (root / "guardian-result").write_text(
                    "INDEPENDENT_RESTORED_REAL_TCP_AND_UDP\n")
                return
        except FenceError as exc:
            if "busy" not in str(exc):
                atomic_journal(root / "guard-blocked.json",
                               {"phase": "blocked", "reason": type(exc).__name__})
                raise
    raise FenceError("guardian timeout: lock never released")


def demo(root):
    root = require_disposable(root)
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    tcp, udp = allocate_port(), allocate_port()
    while tcp == udp:
        udp = allocate_port()
    ports = (tcp, udp)
    oldcmd = server_cmd("legacy", ports)
    old = subprocess.Popen(oldcmd, start_new_session=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    tracked = []
    ctrl = None
    try:
        if not await_probe(*ports, "legacy", 3):
            raise FenceError("initial old service not healthy")
        oldid = proc_identity(old.pid)
        tracked.append((old.pid, oldid.start_ticks))
        atomic_journal(root / "transaction.json",
                       {"phase": "legacy", "old": asdict(oldid), "schema": 1})
        ctrl = subprocess.Popen([sys.executable, "-m",
               "xray.lab.v30_fenced_process_recovery_lab", "--controller",
               str(root), "--tcp", str(tcp), "--udp", str(udp)],
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
               start_new_session=True)
        ctrlticks = proc_stat(ctrl.pid)[2]
        tracked.append((ctrl.pid, ctrlticks))
        deadline = time.monotonic() + 6
        while not (root / "cutover-ready").exists():
            if ctrl.poll() is not None:
                raise FenceError("controller unexpectedly exited")
            if time.monotonic() > deadline:
                raise FenceError("controller never cut over test TCP/UDP")
            time.sleep(0.03)
        assert probe(*ports, "candidate")
        before = read_json(root / "transaction.json")
        tracked.append((before["candidate"]["pid"],
                        before["candidate"]["start_ticks"]))
        guard = read_json(root / "guardian.json")
        tracked.append((guard["pid"], guard["ticks"]))
        ctrl.kill()  # deliberate controlled failure of OWN disposable child
        ctrl.wait(timeout=3)
        deadline = time.monotonic() + 9
        while not (root / "guardian-result").exists():
            if (root / "guard-blocked.json").exists():
                raise FenceError("independent guard entered blocked")
            if time.monotonic() > deadline:
                raise FenceError("independent guard did not restore")
            time.sleep(0.05)
        after = read_json(root / "transaction.json")
        if after["phase"] != "restored" or not probe(*ports, "legacy"):
            raise FenceError("restoration not proven on TCP and UDP")
        tracked.append((after["restored"]["pid"],
                        after["restored"]["start_ticks"]))
        print("PASS: old real TCP and UDP -> candidate real TCP and UDP")
        print("PASS: killed ONLY disposable controller while mutex held")
        print("PASS: independent detached guardian acquired lock and restored old TCP+UDP")
        print("PASS: durable candidate PID/start_ticks journal and bounded recovery")
        print("LIMITATION: fake endpoints, not Xray, not Linux TPROXY, not router reboot")
    finally:
        if ctrl is not None and ctrl.poll() is None:
            ctrl.kill()
            ctrl.wait(timeout=3)
        # Include any process recorded in the private journal in case demo
        # failed between spawn and tracking.
        for filename in ("candidate-prepared.json", "restored-prepared.json",
                         "guardian.json"):
            p = root / filename
            if p.exists():
                rec = read_json(p)
                tracked.append((rec["pid"], rec.get("ticks", rec.get("start_ticks"))))
        for pid, ticks in reversed(tracked):
            if ticks is not None:
                cleanup_lab_pid(pid, ticks)
        if old.poll() is None:
            old.wait(timeout=3)


def main():
    p = argparse.ArgumentParser()
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--server", choices=("legacy", "candidate"))
    mode.add_argument("--controller", type=Path)
    mode.add_argument("--guardian", type=Path)
    mode.add_argument("--demo", type=Path)
    p.add_argument("--tcp", type=int)
    p.add_argument("--udp", type=int)
    a = p.parse_args()
    if a.server:
        # The server is inert without loopback-only ports and can never be
        # used as a real router Xray service.
        if not 1024 <= a.tcp <= 65535 or not 1024 <= a.udp <= 65535:
            raise FenceError("invalid loopback lab ports")
        if Path("/opt/etc/xray/config.json").exists():
            raise FenceError("no server mode on router")
        server(a.server, a.tcp, a.udp)
    elif a.demo:
        demo(a.demo)
    elif a.controller:
        controller(a.controller, (a.tcp, a.udp))
    else:
        guardian(a.guardian, (a.tcp, a.udp))


if __name__ == "__main__":
    main()
