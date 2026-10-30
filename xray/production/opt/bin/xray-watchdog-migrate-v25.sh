#!/opt/bin/sh
# Xray watchdog migration v25.1
# No Xray restart, firewall, routing or cron changes.

exec /opt/bin/python3 - "$@" <<'PY'
import os
import sys
import time
import signal
import socket
import fcntl
import subprocess
from pathlib import Path

OLD = "/opt/bin/xray-watchdog.sh"
NEW = "/opt/bin/xray-watchdog-v25.sh"

OLD_PID = Path("/opt/var/run/xray-watchdog.pid")
NEW_PID = Path("/opt/var/run/xray-watchdog-v25.pid")

LOCK = "/opt/tmp/xray-watchdog-migrate-v25.lock"
LOG = "/opt/tmp/xray-watchdog-migrate-v25.log"

MODES = {"preflight", "activate", "verify", "rollback"}

def log(message):
    line = time.strftime("%Y-%m-%d %H:%M:%S ") + message
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")

def fail(message):
    log("ERROR: " + message)
    raise RuntimeError(message)

def require_pidfd():
    if not hasattr(os, "pidfd_open"):
        fail("PIDFD_OPEN_UNAVAILABLE")
    if not hasattr(signal, "pidfd_send_signal"):
        fail("PIDFD_SIGNAL_UNAVAILABLE")

def read_pid(path):
    try:
        value = path.read_text().strip()
        if not value.isascii() or not value.isdecimal():
            return None
        pid = int(value)
        return pid if pid > 1 else None
    except (OSError, ValueError):
        return None

def cmdline(pid):
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
        return [x.decode("utf-8", "replace")
                for x in raw.split(b"\0") if x]
    except OSError:
        return []

def identity(pid, script):
    if pid is None:
        return False
    return cmdline(pid) == ["/opt/bin/sh", script]

def start_ticks(pid):
    try:
        data = Path(f"/proc/{pid}/stat").read_text()
        return int(data.rsplit(")", 1)[1].split()[19])
    except (OSError, ValueError, IndexError):
        return None

def open_verified_pidfd(pid, script):
    require_pidfd()

    if not identity(pid, script):
        fail("PROCESS_IDENTITY_MISMATCH")

    before = start_ticks(pid)
    if before is None:
        fail("PROCESS_STARTTIME_MISSING")

    fd = os.pidfd_open(pid, 0)

    if not identity(pid, script) or start_ticks(pid) != before:
        os.close(fd)
        fail("PROCESS_CHANGED_DURING_VERIFICATION")

    return fd

def signal_verified(pid, script):
    fd = open_verified_pidfd(pid, script)
    try:
        signal.pidfd_send_signal(fd, signal.SIGTERM, None, 0)
    finally:
        os.close(fd)

def main_ok():
    result = subprocess.run(
        ["/opt/bin/python3",
         "/opt/bin/xray-identity-v24.py"],
        capture_output=True,
        text=True,
        timeout=10
    )
    if result.returncode != 0:
        return False
    return "IDENTITY: VERIFIED" in result.stdout

def socks_ok():
    sock = socket.socket()
    sock.settimeout(2)
    try:
        sock.connect(("127.0.0.1", 10808))
        return True
    except OSError:
        return False
    finally:
        sock.close()

def old_pid():
    pid = read_pid(OLD_PID)
    return pid if identity(pid, OLD) else None

def new_pid():
    pid = read_pid(NEW_PID)
    return pid if identity(pid, NEW) else None

def write_pid_atomic(path, pid):
    tmp = path.with_name(path.name + ".migrate-tmp")
    if tmp.exists():
        fail("TEMP_PIDFILE_EXISTS")
    with open(tmp, "x") as f:
        f.write(str(pid) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)

def preflight():
    require_pidfd()

    for script in (OLD, NEW):
        if not Path(script).is_file():
            fail("SCRIPT_MISSING: " + script)
        result = subprocess.run(
            ["/opt/bin/sh", "-n", script],
            timeout=10
        )
        if result.returncode != 0:
            fail("SCRIPT_SYNTAX: " + script)

    if not main_ok():
        fail("MAIN_XRAY_NOT_VERIFIED")
    if not socks_ok():
        fail("SOCKS5_UNAVAILABLE")

    pid = old_pid()
    if pid is None:
        fail("OLD_WATCHDOG_NOT_VERIFIED")

    fd = open_verified_pidfd(pid, OLD)
    os.close(fd)

    if NEW_PID.exists():
        fail("NEW_PIDFILE_ALREADY_EXISTS")

    log(f"PREFLIGHT_PASS OLD_PID={pid}")
    return pid

def activate():
    old = preflight()
    old_ticks = start_ticks(old)

    process = subprocess.Popen(
        ["/opt/bin/sh", NEW],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )

    try:
        time.sleep(2)

        if not identity(process.pid, NEW):
            fail("NEW_WATCHDOG_NOT_RUNNING")

        if not main_ok() or not socks_ok():
            fail("XRAY_HEALTH_CHECK_FAILED")

        if old_pid() != old or start_ticks(old) != old_ticks:
            fail("OLD_WATCHDOG_CHANGED")

        # Keep the new watchdog if the old one is stopped.
        write_pid_atomic(NEW_PID, process.pid)

        signal_verified(old, OLD)
        log(f"OLD_WATCHDOG_SIGNALLED PID={old}")

        for _ in range(10):
            if not identity(old, OLD):
                break
            time.sleep(0.2)
        else:
            fail("OLD_WATCHDOG_DID_NOT_EXIT")

        if not identity(process.pid, NEW):
            fail("NEW_WATCHDOG_EXITED")

        if not main_ok() or not socks_ok():
            fail("XRAY_CHANGED_AFTER_SWITCH")

        if read_pid(OLD_PID) == old:
            OLD_PID.unlink()

        log(f"ACTIVATED NEW_PID={process.pid}")
        log("AUTOSTART_UNCHANGED")

    except Exception:
        # If the old watchdog is still active, remove
        # only the new process we started.
        if old_pid() == old:
            if identity(process.pid, NEW):
                signal_verified(process.pid, NEW)
            if read_pid(NEW_PID) == process.pid:
                NEW_PID.unlink()
        else:
            log("MANUAL_RECOVERY_REQUIRED")
            log("NEW_WATCHDOG_PRESERVED")
        raise

def verify():
    if not main_ok():
        fail("MAIN_XRAY_NOT_VERIFIED")
    if not socks_ok():
        fail("SOCKS5_UNAVAILABLE")

    pid = new_pid()
    if pid is None:
        fail("NEW_WATCHDOG_NOT_VERIFIED")

    if old_pid() is not None:
        fail("OLD_WATCHDOG_STILL_RUNNING")

    log(f"VERIFY_PASS NEW_PID={pid}")
    log("AUTOSTART_UNCHANGED")

def rollback():
    # Never leave the system without a watchdog
    # by automatically stopping the only observer.
    if old_pid() is None:
        fail("ROLLBACK_REFUSED_NO_OLD_WATCHDOG")

    pid = new_pid()
    if pid is None:
        fail("NEW_WATCHDOG_NOT_VERIFIED")

    signal_verified(pid, NEW)

    for _ in range(10):
        if not identity(pid, NEW):
            break
        time.sleep(0.2)
    else:
        fail("NEW_WATCHDOG_DID_NOT_EXIT")

    if read_pid(NEW_PID) == pid:
        NEW_PID.unlink()

    log("ROLLBACK_PASS")
    log("MAIN_XRAY_UNCHANGED")

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in MODES:
        print("Usage: controller preflight|activate|verify|rollback")
        return 2

    with open(LOCK, "a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("MIGRATION_LOCKED")
            return 1

        try:
            globals()[sys.argv[1]]()
            return 0
        except Exception as exc:
            log(f"FAILED: {type(exc).__name__}: {exc}")
            return 1

sys.exit(main())
PY