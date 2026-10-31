#!/usr/bin/env python3
"""Disposable CI-only pidfd signal gate. No fallback to numeric os.kill()."""
import argparse
import os
import signal
import sys


def start_ticks(pid: int) -> int:
    # /proc/PID/stat comm may include spaces and parentheses.
    raw = open(f"/proc/{pid}/stat", "rb").read()
    end = raw.rfind(b") ")
    if end < 0:
        raise ValueError("invalid /proc stat")
    fields = raw[end + 2:].split()
    # field 3 is index 0; starttime is field 22 -> index 19.
    return int(fields[19])


def guarded_signal(pid: int, expected_ticks: int, sig: int, marker: str) -> bool:
    if pid <= 1 or expected_ticks <= 0 or not marker:
        return False
    if not hasattr(os, "pidfd_open") or not hasattr(signal, "pidfd_send_signal"):
        return False
    fd = None
    try:
        # Pin process identity before checking metadata, never os.kill(pid).
        fd = os.pidfd_open(pid, 0)
        if start_ticks(pid) != expected_ticks:
            return False
        cmdline = open(f"/proc/{pid}/cmdline", "rb").read().replace(b"\0", b" ")
        if marker.encode() not in cmdline:
            return False
        if start_ticks(pid) != expected_ticks:
            return False
        signal.pidfd_send_signal(fd, sig, None, 0)
        return True
    except (OSError, ValueError, ProcessLookupError):
        return False
    finally:
        if fd is not None:
            os.close(fd)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pid", type=int)
    parser.add_argument("start_ticks", type=int)
    parser.add_argument("marker")
    parser.add_argument("--signal", choices=("TERM", "KILL"), default="TERM")
    args = parser.parse_args()
    sig = signal.SIGTERM if args.signal == "TERM" else signal.SIGKILL
    if not guarded_signal(args.pid, args.start_ticks, sig, args.marker):
        print("PIDFD_REFUSE: stale/ambiguous PID or unavailable pidfd", file=sys.stderr)
        return 2
    print("PIDFD_SIGNAL: pinned identity only")
    return 0


if __name__ == "__main__":
    sys.exit(main())
