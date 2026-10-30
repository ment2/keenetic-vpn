#!/usr/bin/env python3
"""EXECUTABLE ISOLATED LAB cutover/rollback simulator. NEVER a router deployer.

Uses fake processes and an in-memory ingress switch, never binds real sockets.
Real TCP/UDP, TPROXY and Xray migration are NOT implemented here.
This intentionally cannot operate on a production Xray or real firewall.
"""
from dataclasses import dataclass
from contextlib import contextmanager
from pathlib import Path
import fcntl
import json
import os
import tempfile
import time


class CutoverError(RuntimeError):
    pass


@dataclass
class FakeProcess:
    pid: int
    start_ticks: int
    alive: bool = True
    socks_ready: bool = True
    tproxy_ready: bool = True
    api_ready: bool = True


class Lab:
    def __init__(self, root, old, candidate):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.old = old
        self.candidate = candidate
        self.owner = "old"
        self.generation = 1
        self.watchdog_fenced = False
        self.kill_switch = True
        self.direct_fallback = False
        self.active_old_tcp = 0
        self.events = []
        self.journal = self.root / "journal.json"
        self.lock_path = self.root / "lock"

    def record(self, phase):
        data = {"phase": phase, "generation": self.generation,
                "owner": self.owner, "watchdog_fenced": self.watchdog_fenced,
                "old_pid": self.old.pid, "old_start_ticks": self.old.start_ticks,
                "candidate_pid": self.candidate.pid,
                "candidate_start_ticks": self.candidate.start_ticks}
        tmp = self.root / "journal.tmp"
        with tmp.open("w") as f:
            json.dump(data, f, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.journal)
        directory = os.open(self.root, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        self.events.append(phase)

    @contextmanager
    def locked(self):
        with self.lock_path.open("a+") as f:
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise CutoverError("another cutover holds lock") from exc
            try:
                yield
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    def safety(self):
        if not self.kill_switch or self.direct_fallback:
            raise CutoverError("fail-closed violation")
        if not self.old.alive and self.owner == "old":
            raise CutoverError("dead old ingress owner")
        if not self.candidate.alive and self.owner == "candidate":
            raise CutoverError("dead candidate ingress owner")

    def cutover(self, *, expected_generation, old_identity, candidate_identity,
                handoff_proven=False, fault=None):
        with self.locked():
            self.safety()
            if self.generation != expected_generation:
                raise CutoverError("stale generation")
            if (self.old.pid, self.old.start_ticks) != old_identity:
                raise CutoverError("old PID/start-ticks changed")
            if (self.candidate.pid, self.candidate.start_ticks) != candidate_identity:
                raise CutoverError("candidate PID/start-ticks changed")
            if not handoff_proven:
                raise CutoverError("real ingress handoff NOT proven")
            if not (self.candidate.alive and self.candidate.socks_ready
                    and self.candidate.tproxy_ready and self.candidate.api_ready):
                raise CutoverError("candidate readiness failed")
            self.watchdog_fenced = True
            self.record("prepared")
            try:
                if fault == "crash_pre_switch":
                    raise CutoverError("injected pre-switch failure")
                self.owner = "candidate"
                self.generation += 1
                self.record("switched")
                if fault == "crash_post_switch":
                    raise CutoverError("injected post-switch failure")
                self.safety()
                if not (self.candidate.socks_ready and self.candidate.tproxy_ready
                        and self.candidate.api_ready):
                    raise CutoverError("post-switch readiness failed")
                self.record("verified")
                # Old TCP sessions remain with old process until separately drained.
                return "SWITCHED_SIMULATION_ONLY"
            except Exception:
                self._rollback_locked()
                raise

    def _rollback_locked(self):
        # This is only a fake ingress pointer, NOT a real TPROXY reversal.
        if self.old.alive and self.old.socks_ready and self.old.tproxy_ready:
            self.owner = "old"
            self.generation += 1
            self.watchdog_fenced = False
            self.record("rolled_back")
        else:
            # Never switch to a dead owner or direct path.
            self.owner = "blocked"
            self.watchdog_fenced = True
            self.record("blocked_requires_local_recovery")

    def rollback(self, *, expected_generation):
        with self.locked():
            self.safety()
            if expected_generation != self.generation:
                raise CutoverError("stale rollback generation")
            self._rollback_locked()

    def recover(self):
        with self.locked():
            if not self.journal.exists():
                raise CutoverError("missing journal")
            previous = json.loads(self.journal.read_text())
            if (previous["old_pid"], previous["old_start_ticks"]) != (
                    self.old.pid, self.old.start_ticks):
                raise CutoverError("old process identity changed")
            if (previous["candidate_pid"], previous["candidate_start_ticks"]) != (
                    self.candidate.pid, self.candidate.start_ticks):
                raise CutoverError("candidate process identity changed")
            if previous["phase"] in ("prepared", "switched"):
                self._rollback_locked()
                return "RECOVERED_SIMULATION_ONLY"
            return "NO_RECOVERY_REQUIRED"


def run_demo():
    with tempfile.TemporaryDirectory(prefix="xray-v30-cutover-lab-") as tmp:
        lab = Lab(tmp, FakeProcess(1001, 110), FakeProcess(1002, 220))
        result = lab.cutover(expected_generation=1, old_identity=(1001, 110),
                             candidate_identity=(1002, 220), handoff_proven=True)
        print(result, lab.events, "old_alive", lab.old.alive)
        print("IMPORTANT: handoff_proven=True is SYNTHETIC, not real TPROXY proof")


if __name__ == "__main__":
    run_demo()
