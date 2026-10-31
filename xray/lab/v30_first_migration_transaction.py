#!/usr/bin/env python3
"""CI-ONLY executable FIRST-cutover transaction and watchdog-race contract.

This is a deliberately non-deployable state machine. It NEVER signals processes,
rewrites router files, changes kernel rules or opens production sockets.
Only a disposable caller-selected journal may be modified. Any attempt to
operate where the Entware production files exist is refused.
"""
from dataclasses import asdict, dataclass, replace
from pathlib import Path
import json
import os
import tempfile
import time


class Rejected(RuntimeError):
    pass


@dataclass(frozen=True)
class Identity:
    pid: int
    start_ticks: int

    def __post_init__(self):
        if self.pid < 2 or self.start_ticks < 1:
            raise Rejected("invalid PID or start_ticks")


@dataclass(frozen=True)
class Evidence:
    old: Identity
    watchdog: Identity
    wifi_repair: Identity
    backup_manifest_ok: bool = False
    active_config_sha_ok: bool = False
    xray_binary_sha_ok: bool = False
    local_ssh_verified: bool = False
    candidate_config_test_ok: bool = False
    legacy_watchdog_fence_proven: bool = False
    wifi_repair_fence_proven: bool = False
    kernel_killswitch_active: bool = False
    no_direct_fallback: bool = False
    route_table_100_active: bool = False
    both_tproxy_protocols_present: bool = False
    no_unknown_xray_processes: bool = False


@dataclass(frozen=True)
class State:
    generation: int = 1
    phase: str = "legacy"
    guard_live: bool = False
    watchdog_fenced: bool = False
    wifi_fenced: bool = False
    old_running: bool = True
    candidate: Identity | None = None
    api_ok: bool = False
    socks_ok: bool = False
    tproxy_tcp_ok: bool = False
    tproxy_udp_ok: bool = False
    openai_via_vpn_ok: bool = False
    dns_ipv6_no_leak_ok: bool = False
    fail_closed_ok: bool = False
    rollback_rebind_proven: bool = False
    supervisor_new_proven: bool = False
    wifi_repair_new_proven: bool = False
    persistent_boot_proven: bool = False
    auto_recovery_tested: bool = False
    # This initial legacy -> API transition breaks old port-owning sockets.
    old_tcp_preserved: bool = False


def preflight(e: Evidence):
    requirements = (
        "backup_manifest_ok", "active_config_sha_ok", "xray_binary_sha_ok",
        "local_ssh_verified", "candidate_config_test_ok",
        "legacy_watchdog_fence_proven", "wifi_repair_fence_proven",
        "kernel_killswitch_active", "no_direct_fallback",
        "route_table_100_active", "both_tproxy_protocols_present",
        "no_unknown_xray_processes",
    )
    missing = tuple(name for name in requirements if getattr(e, name) is not True)
    if len({e.old.pid, e.watchdog.pid, e.wifi_repair.pid}) != 3:
        missing += ("distinct_process_identities",)
    return missing


class Journal:
    """Durable toy journal; refuses production/Entware and symlinked path."""

    def __init__(self, root: Path):
        if Path("/opt/etc/xray/config.json").exists() or Path("/opt/etc/init.d/S97xray").exists():
            raise Rejected("production environment: no simulated transitions on router")
        self.root = Path(root).resolve()
        if str(self.root).startswith(("/opt/", "/etc/", "/var/")):
            raise Rejected("journal may not use production paths")
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.file = self.root / "first-cutover-v30.json"
        if self.file.is_symlink():
            raise Rejected("unsafe journal symlink")

    def save(self, state: State):
        payload = asdict(state)
        if payload["candidate"] is not None:
            payload["candidate"] = asdict(state.candidate)
        fd, name = tempfile.mkstemp(prefix=".txn-", dir=self.root)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.file)
            d = os.open(self.root, os.O_RDONLY)
            try:
                os.fsync(d)
            finally:
                os.close(d)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def load(self):
        data = json.loads(self.file.read_text(encoding="utf-8"))
        if data.get("candidate") is not None:
            data["candidate"] = Identity(**data["candidate"])
        return State(**data)


class Transaction:
    def __init__(self, journal: Journal, evidence: Evidence, initial: State | None = None):
        self.journal, self.evidence = journal, evidence
        self.s = initial or State()
        if preflight(evidence):
            raise Rejected("preflight missing: " + ", ".join(preflight(evidence)))
        if initial is None:
            journal.save(self.s)

    @classmethod
    def recover(cls, journal: Journal, evidence: Evidence):
        return cls(journal, evidence, journal.load())

    def change(self, phase, *, expected_generation, **changes):
        if self.s.generation != expected_generation:
            raise Rejected("generation CAS mismatch")
        self.s = replace(self.s, phase=phase, generation=self.s.generation+1, **changes)
        self.journal.save(self.s)
        return self.s

    def arm(self, expected_generation, *, independent_guard_active, rollback_timeout_seconds):
        if self.s.phase != "legacy":
            raise Rejected("cannot arm from current phase")
        if independent_guard_active is not True or not 30 <= rollback_timeout_seconds <= 120:
            raise Rejected("no bounded independent automatic rollback")
        return self.change("armed", expected_generation=expected_generation, guard_live=True)

    def fence(self, expected_generation, *, watchdog_identity, wifi_identity,
              watchdog_stopped, wifi_stopped, service_paths_fenced):
        if self.s.phase != "armed" or not self.s.guard_live:
            raise Rejected("guard must be armed first")
        if watchdog_identity != self.evidence.watchdog or wifi_identity != self.evidence.wifi_repair:
            raise Rejected("watcher PID reuse/identity mismatch")
        if not (watchdog_stopped and wifi_stopped and service_paths_fenced):
            raise Rejected("watchdog/S98 race not fenced")
        return self.change("fenced", expected_generation=expected_generation,
                           watchdog_fenced=True, wifi_fenced=True)

    def stop_legacy(self, expected_generation, *, old_identity, no_competing_xray):
        if self.s.phase != "fenced" or not (self.s.guard_live and self.s.watchdog_fenced
                                            and self.s.wifi_fenced):
            raise Rejected("no safe stop without independent guard and fences")
        if old_identity != self.evidence.old or not no_competing_xray:
            raise Rejected("stale old process or competing Xray")
        return self.change("legacy_stopped", expected_generation=expected_generation,
                           old_running=False, old_tcp_preserved=False)

    def activate(self, expected_generation, *, candidate: Identity, exclusive_tcp_and_udp):
        if self.s.phase != "legacy_stopped" or self.s.old_running:
            raise Rejected("old listener must be exclusively stopped")
        if candidate == self.evidence.old or not exclusive_tcp_and_udp:
            raise Rejected("new process identity or ingress ownership unproven")
        return self.change("candidate_running", expected_generation=expected_generation,
                           candidate=candidate)

    def verify(self, expected_generation, **gates):
        required = ("api_ok", "socks_ok", "tproxy_tcp_ok", "tproxy_udp_ok",
                    "openai_via_vpn_ok", "dns_ipv6_no_leak_ok", "fail_closed_ok")
        if self.s.phase != "candidate_running":
            raise Rejected("cannot verify before candidate owns ingress")
        if set(gates) != set(required) or any(gates[k] is not True for k in required):
            raise Rejected("full TCP/UDP/API/DNS/IPv6 readiness failed")
        return self.change("candidate_verified", expected_generation=expected_generation, **gates)

    def finish(self, expected_generation, *, new_supervisor, new_wifi_repair,
               boot_persistence, auto_recovery):
        if self.s.phase != "candidate_verified":
            raise Rejected("unverified candidate")
        if not all((new_supervisor, new_wifi_repair, boot_persistence, auto_recovery)):
            raise Rejected("cannot commit with legacy killall watchdog or untested reboot recovery")
        return self.change("api_enabled", expected_generation=expected_generation,
                           guard_live=False, watchdog_fenced=False, wifi_fenced=False,
                           supervisor_new_proven=True, wifi_repair_new_proven=True,
                           persistent_boot_proven=True, auto_recovery_tested=True)

    def rollback(self, expected_generation, *, candidate_identity=None,
                 old_config_readback_ok, old_tcp_udp_bound, watchdog_unfenced, wifi_unfenced):
        if self.s.phase not in ("armed", "fenced", "legacy_stopped", "candidate_running",
                                "candidate_verified", "rolling_back"):
            raise Rejected("no rollback from current phase")
        if self.s.candidate is not None and candidate_identity != self.s.candidate:
            raise Rejected("rollback refuses to kill unknown or reused candidate PID")
        restored = all((old_config_readback_ok, old_tcp_udp_bound,
                        watchdog_unfenced, wifi_unfenced))
        # Cannot claim restored merely because old config is copied.
        return self.change("restored" if restored else "blocked",
                           expected_generation=expected_generation, guard_live=False,
                           watchdog_fenced=not watchdog_unfenced,
                           wifi_fenced=not wifi_unfenced,
                           old_running=bool(old_tcp_udp_bound),
                           rollback_rebind_proven=bool(restored),
                           candidate=None if candidate_identity == self.s.candidate else self.s.candidate)

    def on_guard_timeout(self, expected_generation, *, candidate_identity=None,
                         old_config_readback_ok=False, old_tcp_udp_bound=False,
                         watchdog_unfenced=False, wifi_unfenced=False):
        if not self.s.guard_live:
            raise Rejected("cannot expire unarmed guard")
        return self.rollback(expected_generation, candidate_identity=candidate_identity,
                             old_config_readback_ok=old_config_readback_ok,
                             old_tcp_udp_bound=old_tcp_udp_bound,
                             watchdog_unfenced=watchdog_unfenced,
                             wifi_unfenced=wifi_unfenced)


def synthetic_demo():
    with tempfile.TemporaryDirectory(prefix="xray-v30-first-cutover-lab-") as temp:
        evidence = Evidence(Identity(1234, 101), Identity(2345, 202),
                            Identity(3456, 303), **{
                                k: True for k in Evidence.__dataclass_fields__
                                if k not in ("old", "watchdog", "wifi_repair")
                            })
        journal = Journal(Path(temp))
        txn = Transaction(journal, evidence)
        txn.arm(1, independent_guard_active=True, rollback_timeout_seconds=60)
        txn.fence(2, watchdog_identity=evidence.watchdog, wifi_identity=evidence.wifi_repair,
                  watchdog_stopped=True, wifi_stopped=True, service_paths_fenced=True)
        txn.stop_legacy(3, old_identity=evidence.old, no_competing_xray=True)
        txn.activate(4, candidate=Identity(4567, 404), exclusive_tcp_and_udp=True)
        txn = Transaction.recover(journal, evidence)  # synthetic process/controller crash
        assert txn.s.phase == "candidate_running"
        txn.on_guard_timeout(5, candidate_identity=Identity(4567, 404),
                             old_config_readback_ok=True, old_tcp_udp_bound=True,
                             watchdog_unfenced=True, wifi_unfenced=True)
        assert txn.s.phase == "restored"
        print("V30_FIRST_CUTOVER: PASS synthetic crash/recovery, exact PID and fenced watchdog/S98")
        print("V30_FIRST_CUTOVER: NO SIGNALS, NO REAL LISTENERS, NO ROUTER COMMANDS")
        print("V30_FIRST_CUTOVER: NO APPROVAL OR PRODUCTION CUTOVER")


if __name__ == "__main__":
    synthetic_demo()
