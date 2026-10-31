#!/usr/bin/env python3
"""Disposable independent watchdog/rollback process rehearsal, not router code.

Guard survives parent command return and reloads fsynced journal. The old
service rebind and watchdog unfreeze are SYNTHETIC evidence, not OS commands.
Never run from /opt (Entware); no signals to other processes or network writes.
"""
import argparse
from dataclasses import asdict, fields
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from xray.lab.v30_first_migration_transaction import (
    Evidence, Identity, Journal, Rejected, Transaction,
)


def fixture():
    return Evidence(
        Identity(13546, 100216734),
        Identity(32713, 61575997),
        Identity(24097, 60711544),
        **{f.name: True for f in fields(Evidence)
           if f.name not in ("old", "watchdog", "wifi_repair")}
    )


def assemble(root: Path):
    e = fixture()
    txn = Transaction(Journal(root), e)
    txn.arm(1, independent_guard_active=True, rollback_timeout_seconds=30)
    txn.fence(2, watchdog_identity=e.watchdog, wifi_identity=e.wifi_repair,
              watchdog_stopped=True, wifi_stopped=True, service_paths_fenced=True)
    txn.stop_legacy(3, old_identity=e.old, no_competing_xray=True)
    txn.activate(4, candidate=Identity(20333, 98765), exclusive_tcp_and_udp=True)
    return txn


def guard(root: Path, *, delay, simulate_restore):
    journal = Journal(root)
    # A detached guard must read its own durable journal; it gets no
    # in-memory reference to the launching transaction/controller.
    state = journal.load()
    if state.phase != "candidate_running" or state.generation != 5 or not state.guard_live:
        raise Rejected("invalid durable recovery state")
    time.sleep(delay)
    transaction = Transaction.recover(journal, fixture())
    assert transaction.s.generation == 5
    result = transaction.on_guard_timeout(5, candidate_identity=Identity(20333, 98765),
            old_config_readback_ok=simulate_restore,
            old_tcp_udp_bound=simulate_restore,
            watchdog_unfenced=simulate_restore,
            wifi_unfenced=simulate_restore)
    assert result.phase == ("restored" if simulate_restore else "blocked")
    (root / "guard-result").write_text(
        "SYNTHETIC_" + result.phase.upper() + "_NO_PROCESS_SIGNALS\n")
    return result.phase


def stage(root: Path, *, simulate_restore):
    root = root.resolve()
    if not str(root).startswith(("/tmp/", "/home/runner/work/", "/home/oai/")):
        raise Rejected("disposable filesystem only")
    Journal(root)
    assemble(root)
    cmd = [sys.executable, "-m", "xray.lab.v30_autonomous_guard_rehearsal",
           "--guard", str(root), "--delay", "0.4", "--restore", str(int(simulate_restore))]
    with (root / "guard-output.log").open("w") as log:
        p = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=log,
                             stderr=subprocess.STDOUT, start_new_session=True)
    (root / "guard-launch.json").write_text(json.dumps({"pid": p.pid, "synthetic": True}))
    print("V30_GUARD_LAB: DETACHED guardian launched (not router). PID recorded", flush=True)


def verify(root: Path, *, simulate_restore):
    expected = "restored" if simulate_restore else "blocked"
    journal = Journal(root)
    for _ in range(60):
        try:
            saved = journal.load()
            if saved.phase == expected:
                result = (root / "guard-result").read_text()
                assert result == "SYNTHETIC_" + expected.upper() + "_NO_PROCESS_SIGNALS\n"
                print("V30_GUARD_LAB: PASS independent detached guard recovered journal; phase="+expected)
                print("V30_GUARD_LAB: NEVER kills Xray, freezes watchdog or modifies firewall")
                return
        except FileNotFoundError:
            pass
        time.sleep(0.1)
    raise Rejected("guard did not finalize synthetic rollback in 6 sec")


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--stage", type=Path)
    group.add_argument("--verify", type=Path)
    group.add_argument("--guard", type=Path)
    parser.add_argument("--delay", type=float, default=0.4)
    parser.add_argument("--restore", choices=["0", "1"], default="1")
    args = parser.parse_args()
    simulate_restore = args.restore == "1"
    if args.stage:
        stage(args.stage, simulate_restore=simulate_restore)
    elif args.verify:
        verify(args.verify, simulate_restore=simulate_restore)
    else:
        guard(args.guard, delay=args.delay, simulate_restore=simulate_restore)


if __name__ == "__main__":
    main()
