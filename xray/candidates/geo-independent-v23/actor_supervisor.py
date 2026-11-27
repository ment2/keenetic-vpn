"""Review-only actor supervisor and ownership contracts.

No live service CLI. All executable actor operations below require the
disposable Migration instance. Native process adoption is deliberately
blocked without a real PID handle; a PID file is never signal authority.
"""
import os
from pathlib import Path
import signal
import stat
import subprocess
import time
from dataclasses import dataclass
from release_gate import require, Blocked

@dataclass(frozen=True)
class Identity:
    boot: str
    pid: int
    start: int
    ppid: int
    exe_dev: int
    exe_ino: int
    argv: tuple

def identity(pid,proc=Path("/proc")):
    require(type(pid) is int and pid>1,"invalid PID")
    p=proc/str(pid)
    def snapshot():
        fields=(p/"stat").read_text().rsplit(")",1)[1].split()
        return int(fields[19]),int(fields[1]),fields[0]
    a=snapshot()
    require(a[2] not in ("Z","X"),"process exited")
    exe=(p/"exe").stat()
    argv=tuple((p/"cmdline").read_bytes().rstrip(b"\0").split(b"\0"))
    boot=(proc/"sys/kernel/random/boot_id").read_text().strip()
    require(a==snapshot() and bool(argv[0]),"process identity changed")
    return Identity(boot,pid,a[0],a[1],exe.st_dev,exe.st_ino,argv)

def match_main(pid,exe,config,proc=Path("/proc")):
    current=identity(pid,proc)
    s=Path(exe).stat()
    require((current.exe_dev,current.exe_ino)==(s.st_dev,s.st_ino)
            and current.argv==(os.fsencode(exe),b"run",b"-config",os.fsencode(config)),
            "not exact main Xray")
    return current

def listener_owned(pid,port,proc=Path("/proc")):
    try:
        endpoint="0100007F:%04X"%port
        rows=[l.split() for l in (proc/"net/tcp").read_text().splitlines()[1:]]
        inodes={r[9] for r in rows if len(r)>9 and r[1].upper()==endpoint and r[3]=="0A"}
        if len(inodes)!=1:return False
        inode=next(iter(inodes))
        for fd in (proc/str(pid)/"fd").iterdir():
            try:
                if os.readlink(fd)=="socket:[%s]"%inode:return True
            except OSError:pass
    except (OSError,ValueError):pass
    return False

class Handle:
    """Linux pidfd binds a signal to the kernel process, never a reused PID."""
    def __init__(self,expected):
        require(hasattr(os,"pidfd_open") and hasattr(signal,"pidfd_send_signal"),"PIDFD unavailable")
        self.expected=expected
        self.fd=os.pidfd_open(expected.pid)
        try:require(identity(expected.pid)==expected,"stale identity")
        except BaseException:os.close(self.fd);raise
    def close(self):os.close(self.fd)
    def terminate(self):
        require(identity(self.expected.pid)==self.expected,"identity changed")
        signal.pidfd_send_signal(self.fd,signal.SIGTERM)
    def __enter__(self):return self
    def __exit__(self,*_):self.close()

class OwnedChild:
    """Single-threaded direct-child supervisor, no PID adoption.

    Parent never reaps child until after signalling is finished. A dead
    unreaped child retains its PID; no unrelated process can reuse it.
    Refuse SIGCHLD auto-reap or an external reaper. Native integration
    must keep this supervisor alive and independently fence its lifetime.
    """
    def __init__(self,argv):
        import threading
        require(threading.active_count()==1 and signal.getsignal(signal.SIGCHLD)==signal.SIG_DFL,"exclusive reaper required")
        self.pid=os.fork()
        if self.pid==0:
            try:os.execv(argv[0],argv)
            finally:os._exit(127)
        self.reaped=False
        self.owner=os.getpid()
    def stop(self,timeout=2):
        require(os.getpid()==self.owner and not self.reaped,"not owned child")
        require(signal.getsignal(signal.SIGCHLD)==signal.SIG_DFL,"reaper changed")
        # No poll/waitpid before signal: PID is still reserved to child.
        os.kill(self.pid,signal.SIGTERM)
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            pid,_=os.waitpid(self.pid,os.WNOHANG)
            if pid:
                self.reaped=True;return
            time.sleep(.02)
        # Last WNOHANG returned 0; child remains ours even if now zombie.
        os.kill(self.pid,signal.SIGKILL)
        os.waitpid(self.pid,0);self.reaped=True

class Actors:
    """S97, watchdog, S98, cron and RC2 review contracts.

    Only explicit top-level gate entry, delegation is an in-process
    callback, not a shell flag, token, argv or environment variable.
    Native wrapper/S97 rewrite and exact rule repair still require review.
    """
    def __init__(self,migration,release,*,restart,healthy,rules_ok,repair,monitor):
        from lock_migration import Migration
        require(isinstance(migration,Migration),"fixture migration required")
        self.m=migration;self.r=release
        self.restart=restart;self.healthy=healthy;self.rules_ok=rules_ok
        self.repair=repair;self.monitor=monitor
    def s97(self):
        return self.m.run("S97",lambda _:self.restart(),gate=self.r)
    def watchdog(self):
        def tick(_):
            if self.healthy():return 0
            # Single outer lock; no nested top-level S97 invocation.
            rc=self.restart()
            return 0 if rc==0 and self.healthy() else 1
        return self.m.run("watchdog",tick,gate=self.r)
    def s98(self):
        def tick(_):
            if self.rules_ok():return 0
            rc=self.repair()
            return 0 if rc==0 and self.rules_ok() else 1
        return self.m.run("S98",tick,gate=self.r)
    def cron(self):return self.m.release(self.r,"cron")
    def rc2(self):return self.m.release(self.r,"monitor",runner=self.monitor)
