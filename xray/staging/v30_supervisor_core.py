#!/usr/bin/env python3
"""Staging-only reusable primitives for Xray v30 cooperative supervision.

NOT an installed service or approved production cutover. No automatic router
actions on import. All lifecycle entrants must acquire the SAME flock inode;
stopping a shell parent is not sufficient fencing.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import json
import os
from pathlib import Path
import signal
import tempfile
import time


class FenceError(RuntimeError):
    pass


@dataclass(frozen=True)
class Identity:
    pid: int
    start_ticks: int
    exe: str
    argv: tuple[str, ...]

    def __post_init__(self):
        if self.pid <= 1 or self.start_ticks <= 0 or not self.exe or not self.argv:
            raise FenceError("invalid process identity")


def proc_stat(pid, proc_root="/proc"):
    """stat position after final ')' tolerates spaces and ')' in comm."""
    if not isinstance(pid, int) or pid <= 1:
        raise FenceError("bad PID")
    try:
        data = (Path(proc_root) / str(pid) / "stat").read_text()
        tail = data.rsplit(")", 1)[1].split()
        return tail[0], int(tail[1]), int(tail[19])
    except (OSError, ValueError, IndexError) as exc:
        raise FenceError("unavailable process identity") from exc


def proc_identity(pid, proc_root="/proc"):
    state, ppid, ticks = proc_stat(pid, proc_root)
    if state in ("Z", "X"):
        raise FenceError("terminated or zombie process")
    root = Path(proc_root) / str(pid)
    try:
        exe = str((root / "exe").resolve(strict=True))
        argv = tuple(x.decode("utf-8", errors="surrogateescape")
                     for x in (root / "cmdline").read_bytes().split(b"\x00") if x)
    except (OSError, RuntimeError) as exc:
        raise FenceError("process executable/argv inaccessible") from exc
    if not argv:
        raise FenceError("empty process argv")
    return Identity(pid, ticks, exe, argv)


def validate_identity(expected, proc_root="/proc"):
    current = proc_identity(expected.pid, proc_root)
    if current != expected:
        raise FenceError("PID/start_ticks/executable/argv changed")
    return current


@contextmanager
def supervisor_lock(path, *, timeout=2.0):
    """One cooperative inode shared by S97, S98, watchdog and cutover.

    A lock cannot protect against unmodified independent scripts. Those
    must be replaced and checked independently before any real cutover.
    """
    path = Path(path)
    if path.is_symlink():
        raise FenceError("symlink supervisor lock")
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    try:
        if not os.path.isfile(path) or os.stat(path).st_ino != os.fstat(fd).st_ino:
            raise FenceError("lock identity changed")
        if os.fstat(fd).st_uid != os.geteuid():
            raise FenceError("lock owned by another UID")
        if (os.fstat(fd).st_mode & 0o777) != 0o600:
            raise FenceError("lock mode is not private")
        until = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= until:
                    raise FenceError("supervisor lock busy; fail closed")
                time.sleep(0.02)
        # Verify inode again while holding the lock. In production the
        # parent directory must also be root-owned 0700 and immutable.
        if os.stat(path).st_ino != os.fstat(fd).st_ino:
            raise FenceError("supervisor lock path swapped")
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def scoped_signal(expected, sig, *, proc_root="/proc"):
    """Refuse PID reuse: kernel pidfd is mandatory, no os.kill fallback."""
    if not hasattr(os, "pidfd_open") or not hasattr(signal, "pidfd_send_signal"):
        raise FenceError("kernel/Python pidfd signaling unavailable")
    validate_identity(expected, proc_root)
    try:
        fd = os.pidfd_open(expected.pid, 0)
    except OSError as exc:
        raise FenceError("pidfd_open failed") from exc
    try:
        validate_identity(expected, proc_root)
        signal.pidfd_send_signal(fd, sig, None, 0)
    except (OSError, ProcessLookupError) as exc:
        raise FenceError("pidfd signal failed") from exc
    finally:
        os.close(fd)


def atomic_journal(path, data):
    """Private, fsynced, replace-only transaction record."""
    path = Path(path)
    if path.is_symlink():
        raise FenceError("journal symlink")
    fd, tmp = tempfile.mkstemp(prefix=".v30-txn-", dir=str(path.parent))
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        fd = -1
        os.replace(tmp, path)
        directory = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if fd >= 0:
            os.close(fd)
        if os.path.exists(tmp):
            os.unlink(tmp)


def gated_spawn(executable, argv, journal, *, proc_root="/proc"):
    """Child remains inert until parent fsyncs PID+start_ticks journal.

    On parent crash before journal: pipe EOF => child exits without exec.
    Must be called only while owning supervisor_lock and with independent
    guardian already proven. Caller still must verify exe+argv AFTER exec.
    """
    if not os.path.isabs(executable) or not argv or argv[0] != executable:
        raise FenceError("bad executable/argv")
    journal = Path(journal)
    readfd, writefd = os.pipe()
    try:
        pid = os.fork()
        if pid == 0:
            os.close(writefd)
            try:
                consent = os.read(readfd, 1)
                os.close(readfd)
                if consent != b"1":
                    os._exit(125)
                os.execv(executable, argv)
            except BaseException:
                os._exit(126)
        os.close(readfd)
        readfd = -1
        try:
            for _ in range(200):
                try:
                    state, _, started = proc_stat(pid, proc_root)
                    if state not in ("Z", "X"):
                        break
                except FenceError:
                    pass
                time.sleep(0.005)
            else:
                raise FenceError("child identity was not obtained before exec")
            atomic_journal(journal, {"phase": "candidate_prepared",
                       "pid": pid, "start_ticks": started, "executable": executable,
                       "argv": argv, "schema": 1})
            os.write(writefd, b"1")
            return (pid, started)
        except BaseException:
            os.close(writefd)
            writefd = -1
            try:
                os.waitpid(pid, 0)
            except ChildProcessError:
                pass
            raise
    finally:
        if readfd >= 0:
            os.close(readfd)
        if writefd >= 0:
            os.close(writefd)


def lock_contract_proof(entrypoints, lock_path):
    """Static release gate; all entrypoint paths must be exact same lock."""
    if not entrypoints or any(not x.get("requires_lock") or
                              x.get("lock_path") != str(lock_path)
                              for x in entrypoints):
        raise FenceError("uncoordinated supervisor entrypoint")
    roles = {x.get("role") for x in entrypoints}
    if roles != {"S97", "S98", "watchdog", "cutover", "guardian"}:
        raise FenceError("missing supervisor actor")
    return True
