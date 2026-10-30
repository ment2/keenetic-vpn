#!/opt/bin/python3
"""Watchdog migration v26: non-mutating safety gate."""

import socket
import subprocess
import sys
from pathlib import Path

OLD = "/opt/bin/xray-watchdog.sh"
NEW = "/opt/bin/xray-watchdog-v25.sh"
OLD_PID = Path("/opt/var/run/xray-watchdog.pid")
NEW_PID = Path("/opt/var/run/xray-watchdog-v25.pid")
STARTUP = Path("/opt/etc/init.d/S99xray-watchdog")
XRAY_ID = "/opt/bin/xray-identity-v24.py"


def identity(path, script):
    try:
        raw = path.read_text().strip()
        if not raw.isascii() or not raw.isdecimal():
            return None
        pid = int(raw)
        if pid <= 1:
            return None

        root = Path(f"/proc/{pid}")
        cmd = [
            part.decode(errors="replace")
            for part in
            (root / "cmdline").read_bytes().split(b"\0")
            if part
        ]
        stat = (root / "stat").read_text()
        ticks = int(stat.rsplit(")", 1)[1].split()[19])

        if cmd != ["/opt/bin/sh", script]:
            return None

        return pid, ticks
    except (OSError, ValueError, IndexError):
        return None


def main_xray_ok():
    try:
        result = subprocess.run(
            ["/opt/bin/python3", XRAY_ID],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return (
            result.returncode == 0
            and "IDENTITY: VERIFIED" in result.stdout
            and "SIGNAL_SENT: NO" in result.stdout
        )
    except (OSError, subprocess.TimeoutExpired):
        return False


def socks_ok():
    try:
        with socket.create_connection(
            ("127.0.0.1", 10808), timeout=2
        ):
            return True
    except OSError:
        return False


def main():
    if len(sys.argv) != 2:
        print("Usage: controller status|plan")
        return 2

    mode = sys.argv[1]
    if mode not in ("status", "plan"):
        print("UNSUPPORTED_MODE")
        return 2

    old = identity(OLD_PID, OLD)
    new = identity(NEW_PID, NEW)

    try:
        startup = STARTUP.read_text()
        startup_old = f"SCRIPT={OLD}" in startup
    except OSError:
        startup_old = False

    checks = {
        "MAIN_XRAY": main_xray_ok(),
        "SOCKS5": socks_ok(),
        "OLD_WATCHDOG": old is not None,
        "NEW_WATCHDOG_ABSENT": new is None,
        "NEW_PIDFILE_ABSENT": not NEW_PID.exists(),
        "STARTUP_OLD": startup_old,
        "OLD_SCRIPT_EXISTS": Path(OLD).is_file(),
        "NEW_SCRIPT_EXISTS": Path(NEW).is_file(),
    }

    for name, ok in checks.items():
        print(f"{name}: {'PASS' if ok else 'FAIL'}")

    if old:
        print(f"OLD_PID: {old[0]}")
        print(f"OLD_START_TICKS: {old[1]}")

    if mode == "plan":
        print("STEP_1: VERIFY_FAIL_CLOSED_ROUTING")
        print("STEP_2: PREPARE_RECOVERY_WATCHDOG")
        print("STEP_3: BACKUP_STARTUP")
        print("STEP_4: VERIFY_PROCESS_IDENTITIES")
        print("STEP_5: SEPARATELY_APPROVE_SWITCH")
        print("STEP_6: VERIFY_AND_RECOVER_IF_NEEDED")

    print("SIGNALS_SENT: NO")
    print("FILES_CHANGED: NO")
    print("MIGRATION_ACTIVATED: NO")

    if not all(checks.values()):
        print("SAFETY_GATE: FAIL")
        return 1

    print("SAFETY_GATE: PASS")
    print("ACTIVATION: NOT_IMPLEMENTED")
    return 0


if __name__ == "__main__":
    sys.exit(main())