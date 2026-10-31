#!/usr/bin/env python3
"""STAGING-ONLY v30 cooperative canary release gate.

This module joins the same flock inode as staged S97/S98/watchdog/guardian.
It intentionally implements NO live --trial or rollback. The currently
installed exact-SHA first_cutover_canary remains unchanged and must NOT
be paired with new init scripts, because it has incompatible source pins
and uses a different transaction lock.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path

from xray.staging.v30_supervisor_core import FenceError, lock_contract_proof, supervisor_lock
from xray.staging.v30_supervisor_service import RouterPaths

ROOT = Path(__file__).resolve().parents[2]
STAGING = ROOT / "xray/staging"
ACTORS = ("S97", "S98", "watchdog", "cutover", "guardian")
TEMPLATES = (
    "S97xray", "S98xray-wifi", "S99xray-watchdog",
    "xray-watchdog.sh", "xray-wifi-rules.sh",
)
STAGING_TEMPLATES = STAGING / "v30_supervisor_templates"
SHARED_LOCK = RouterPaths.lock


def actor_contract(lock=SHARED_LOCK):
    """One path/inode contract for all five cooperative actors."""
    rows = [{"role": x, "requires_lock": True, "lock_path": str(lock)}
            for x in ACTORS]
    lock_contract_proof(rows, lock)
    if lock != SHARED_LOCK:
        raise FenceError("different lock from installed service broker")
    return rows


@contextmanager
def coordinated_trial_lock(*, lock=SHARED_LOCK, no_legacy_writers=False):
    """Fail closed until legacy cron/init/watchdog descendants are drained.

    A held lock is necessary but not sufficient: unfenced legacy tasks
    do not cooperate, so an explicit externally verified gate is required.
    """
    actor_contract(lock)
    if no_legacy_writers is not True:
        raise FenceError("legacy restart/rule repair still not fenced")
    with supervisor_lock(lock):
        yield


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def release_bundle_checks():
    """Inspect only staged repository artifacts, never router or secrets."""
    if SHARED_LOCK != Path("/opt/var/run/xray-v30-supervisor.lock"):
        raise FenceError("service/canary shared lock mismatch")
    source = (STAGING / "v30_supervisor_service.py").read_text()
    core = (STAGING / "v30_supervisor_core.py").read_text()
    if not all(x in source for x in (
            "with supervisor_lock(self.p.lock)",
            "scoped_signal(old, signal.SIGTERM)",
            "def actor_control(", "def wifi_once(")):
        raise FenceError("supervisor does not enforce cooperative lock")
    if not all(x in core for x in ("pidfd_send_signal(", "flock(", "def gated_spawn(")):
        raise FenceError("supervisor core identity/fencing primitives missing")
    files = {}
    for name in TEMPLATES:
        p = STAGING_TEMPLATES / name
        if not p.is_file() or p.is_symlink():
            raise FenceError("missing/symlinked staged entrypoint")
        executable = "\n".join(x for x in p.read_text().splitlines()
                               if not x.lstrip().startswith("#"))
        if ("v30_supervisor_service.py" not in executable or
                "killall " in executable or
                "/opt/sbin/iptables " in executable or
                "xray-wifi-rules.sh " in executable):
            raise FenceError("unfenced staged entrypoint")
        files[name] = sha(p)
    return {
        "phase": "STAGING_ONLY",
        "common_lock": str(SHARED_LOCK),
        "actors": [x["role"] for x in actor_contract()],
        "template_sha256": files,
        "broker_sha256": sha(STAGING / "v30_supervisor_service.py"),
        "core_sha256": sha(STAGING / "v30_supervisor_core.py"),
        "installed_canary_compatible": False,
        "legacy_supervisors_replaced": False,
        "guardian_reboot_verified": False,
        "production_trial_allowed": False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--offline-plan", action="store_true")
    args = p.parse_args()
    if not args.offline_plan:
        p.error("only --offline-plan is implemented; no live cutover")
    print(json.dumps(release_bundle_checks(), sort_keys=True))


if __name__ == "__main__":
    main()
