#!/opt/bin/python3

import os
import sys
import fcntl
from pathlib import Path

XRAY = "/opt/sbin/xray"
CONFIG = "/opt/etc/xray/config.json"
LOCK = "/opt/tmp/xray-control.lock"

EXPECTED = [
    XRAY,
    "run",
    "-config",
    CONFIG,
]


def identity(pid):
    proc = Path("/proc") / str(pid)

    raw = (proc / "cmdline").read_bytes()
    args = [
        x.decode("utf-8", "replace")
        for x in raw.split(b"\0")
        if x
    ]

    stat = (proc / "stat").read_text()
    tail = stat[stat.rfind(")") + 2:].split()

    start_ticks = int(tail[19])

    return args, start_ticks


def find_main():
    matches = []

    for name in os.listdir("/proc"):
        if not name.isdigit():
            continue

        pid = int(name)

        try:
            args, ticks = identity(pid)
        except (OSError, ValueError, IndexError):
            continue

        if args == EXPECTED:
            matches.append((pid, ticks))

    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one main Xray, found {len(matches)}"
        )

    return matches[0]


def verify(pid, ticks):
    args2, ticks2 = identity(pid)

    if args2 != EXPECTED or ticks2 != ticks:
        raise RuntimeError("Xray process identity changed")

    return True


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("status", "dry-run"):
        print("USAGE: xray-control-v24-next.py status|dry-run")
        return 2

    fd = os.open(LOCK, os.O_CREAT | os.O_RDWR, 0o600)

    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("CONTROL_LOCK: BUSY")
            return 3

        pid, ticks = find_main()
        verify(pid, ticks)

        print("CONTROL_LOCK: ACQUIRED")
        print("MAIN_PID:", pid)
        print("START_TICKS:", ticks)
        print("IDENTITY: VERIFIED")

        if sys.argv[1] == "dry-run":
            print("STOP_TARGET:", pid)
            print("STOP_AUTHORIZED: NO")
            print("SIGNAL_SENT: NO")
            print("DRY_RUN: PASS")
        else:
            print("STATUS: OK")

        return 0

    finally:
        os.close(fd)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("ERROR:", type(exc).__name__, str(exc))
        sys.exit(1)