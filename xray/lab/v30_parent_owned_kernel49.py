#!/usr/bin/env python3
"""LAB ONLY: Linux 4.9-compatible direct-parent-owned Xray child prototype.

A PID is safe to signal only while the *sole reaper* has not reaped its
direct child. Child sets PR_SET_PDEATHSIG=SIGKILL before exec and verifies
its parent after the prctl call. No pidfd, no 'killall', no signalling a
journal PID from a guardian. A parent crash causes its child to die;
a separate guardian can only wait for verified absence and start a NEW
owned process; it cannot safely adopt or kill an orphan by stale PID.

This is an engineering prototype, NOT a replaceable Entware supervisor.
"""
import ctypes
from dataclasses import dataclass
import errno
import os
from pathlib import Path
import signal
import time

from xray.staging.v30_supervisor_core import FenceError, atomic_journal, proc_stat

PR_SET_PDEATHSIG = 1


@dataclass(frozen=True)
class Owned:
    pid: int
    ticks: int
    parent_pid: int
    argv: tuple[str, ...]


def _pdeathsig(sig):
    if os.name != "posix" or not Path("/proc/self/stat").exists():
        raise FenceError("Linux only")
    c = ctypes.CDLL(None, use_errno=True)
    if c.prctl(PR_SET_PDEATHSIG, int(sig), 0, 0, 0) != 0:
        raise FenceError("PR_SET_PDEATHSIG failed errno=" + str(ctypes.get_errno()))


def child_owner_status(child):
    """WNOWAIT keeps zombie PID reserved until *this parent* reaps it."""
    if os.getpid() != child.parent_pid:
        raise FenceError("cannot control another parent's child")
    try:
        state, ppid, ticks = proc_stat(child.pid)
        if ppid != child.parent_pid or ticks != child.ticks:
            raise FenceError("direct-child identity changed")
        info = os.waitid(os.P_PID, child.pid,
                         os.WEXITED | os.WNOHANG | os.WNOWAIT)
    except (ChildProcessError, OSError, ValueError) as exc:
        raise FenceError("no sole-reaper guarantee") from exc
    if info is not None:
        return "EXITED_UNREAPED"
    if state in ("Z", "X"):
        return "EXITED_UNREAPED"
    return "ALIVE_OWNED"


def owned_signal(child, sig):
    """No PID reuse: direct child can only be reaped by this sole reaper.

    Never set SIGCHLD=SIG_IGN, SA_NOCLDWAIT, auto-reaping handlers, or
    call waitpid/waitid without WNOWAIT before this function finishes.
    """
    status = child_owner_status(child)
    if status != "ALIVE_OWNED":
        return "ALREADY_EXITED_UNREAPED"
    os.kill(child.pid, sig)  # ONLY direct unreaped child
    return "SENT_TO_DIRECT_CHILD_WITH_RESERVED_PID"


def spawn_owned(executable, argv, journal, *, on_prepared=None):
    """Release forked child only AFTER fsynced parent+child identity journal."""
    if not os.path.isabs(executable) or not argv or argv[0] != executable:
        raise FenceError("absolute executable/argv required")
    if signal.getsignal(signal.SIGCHLD) == signal.SIG_IGN:
        raise FenceError("auto-reap SIGCHLD forbidden")
    journal = Path(journal)
    if journal.exists() or journal.is_symlink():
        raise FenceError("unreconciled prepared child journal")
    parent = os.getpid()
    rfd, wfd = os.pipe()
    try:
        pid = os.fork()
        if pid == 0:
            os.close(wfd)
            try:
                _pdeathsig(signal.SIGKILL)
                if os.getppid() != parent:
                    os._exit(125)
                if os.read(rfd, 1) != b"G":
                    os._exit(125)
                os.close(rfd)
                os.execv(executable, argv)
            except BaseException:
                os._exit(126)
        os.close(rfd)
        rfd = -1
        try:
            # Child must not exec before journal. It is alive but blocked
            # on gate pipe, and parent still owns its unreaped PID.
            end = time.monotonic() + 2
            while True:
                state, ppid, ticks = proc_stat(pid)
                if ppid != parent or ticks <= 0 or state in ("Z", "X"):
                    raise FenceError("pre-exec child ownership missing")
                break
            child = Owned(pid, ticks, parent, tuple(argv))
            atomic_journal(journal, {
                "phase": "PREPARED_PARENT_OWNED",
                "pid": pid, "start_ticks": ticks,
                "parent_pid": parent, "argv": list(argv),
                "pdeathsig": "SIGKILL", "pidfd_required": False})
            if on_prepared is not None:
                on_prepared(child)
            os.write(wfd, b"G")
            return child
        except BaseException:
            # Broken gate/EOF causes child to exit before exec. No global
            # kill, no signal to unverified PID.
            os.close(wfd)
            wfd = -1
            os.waitpid(pid, 0)
            raise
    finally:
        if rfd >= 0:
            os.close(rfd)
        if wfd >= 0:
            os.close(wfd)


def reap_owned(child, timeout=5):
    if os.getpid() != child.parent_pid:
        raise FenceError("only owner can reap")
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        status = child_owner_status(child)
        if status == "EXITED_UNREAPED":
            actual, wait_status = os.waitpid(child.pid, 0)
            if actual != child.pid:
                raise FenceError("wrong child was reaped")
            return wait_status
        time.sleep(0.025)
    raise FenceError("child did not exit before timeout")
