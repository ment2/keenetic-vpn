#!/opt/bin/python3
"""Xray watchdog migration v25.2: safe preflight only."""
import os
import socket
import subprocess
import sys
from pathlib import Path

OLD = "/opt/bin/xray-watchdog.sh"
NEW = "/opt/bin/xray-watchdog-v25.sh"
OLD_PID = Path("/opt/var/run/xray-watchdog.pid")
NEW_PID = Path("/opt/var/run/xray-watchdog-v25.pid")
STARTUP = Path("/opt/etc/init.d/S99xray-watchdog")
IDENTITY = "/opt/bin/xray-identity-v24.py"


def pid_from(path):
    try:
        value = path.read_text().strip()
        if not value.isascii() or not value.isdecimal():
            return None
        pid = int(value)
        return pid if pid > 1 else None
    except (OSError, ValueError):
        return None


def process_info(pid):
    if pid is None:
        return None
    try:
        root = Path(f"/proc/{pid}")
        argv = [
            x.decode("utf-8", "replace")
            for x in (root / "cmdline").read_bytes().split(b"\0")
            if x
        ]
        stat = (root / "stat").read_text()
        ticks = int(stat.rsplit(")", 1)[1].split()[19])
        return argv, ticks
    except (OSError, ValueError, IndexError):
        return None


def verified_process(path, script):
    pid = pid_from(path)
    info = process_info(pid)
    if info is None:
        return None
    if info[0] != ["/opt/bin/sh", script]:
        return None
    return pid, info[1]


def check_script(path):
    if not Path(path).is_file():
        return False
    try:
        result = subprocess.run(
            ["/opt/bin/sh", "-n", path],
            timeout=10,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def xray_ok():
    try:
        result = subprocess.run(
            ["/opt/bin/python3", IDENTITY],
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
    if len(sys.argv) != 2 or sys.argv[1] != "preflight":
        print("Usage: controller preflight")
        return 2

    checks = {
        "OLD_SCRIPT_SYNTAX": check_script(OLD),
        "NEW_SCRIPT_SYNTAX": check_script(NEW),
        "MAIN_XRAY": xray_ok(),
        "SOCKS5": socks_ok(),
        "OLD_WATCHDOG": verified_process(
            OLD_PID, OLD
        ) is not None,
        "NEW_PIDFILE_ABSENT": not NEW_PID.exists(),
        "STARTUP_EXISTS": STARTUP.is_file(),
        "STARTUP_UNCHANGED": False,
    }

    try:
        startup = STARTUP.read_text()
        checks["STARTUP_UNCHANGED"] = (
            f"SCRIPT={OLD}" in startup
        )
    except OSError:
        pass

    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    old = verified_process(OLD_PID, OLD)
    if old:
        print(f"OLD_PID: {old[0]}")
        print(f"OLD_START_TICKS: {old[1]}")

    print("PROCESSES_CHANGED: NO")
    print("CONFIG_CHANGED: NO")
    print("SIGNALS_SENT: NO")
    print("MIGRATION_ACTIVATED: NO")

    passed = all(checks.values())
    print("PREFLIGHT:", "PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())