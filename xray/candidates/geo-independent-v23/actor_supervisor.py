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
        import threading
        require(threading.active_count()==1 and signal.getsignal(signal.SIGCHLD)==signal.SIG_DFL,"reaper changed")
        # Establish direct-child ownership with waitpid. If the child is
        # already dead, reap it and never signal. If it is not dead, the
        # exclusive parent retains the PID until it reaps it.
        pid,_=os.waitpid(self.pid,os.WNOHANG)
        if pid:
            self.reaped=True;return
        os.kill(self.pid,signal.SIGTERM)
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            pid,_=os.waitpid(self.pid,os.WNOHANG)
            if pid:
                self.reaped=True;return
            time.sleep(.02)
        # Last WNOHANG returned 0; child remains ours even if now zombie.
        os.kill(self.pid,signal.SIGKILL)
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            pid,_=os.waitpid(self.pid,os.WNOHANG)
            if pid:
                self.reaped=True;return
            time.sleep(.02)
        raise Blocked("child termination not observed")

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
    def cron(self,apply=None):
        if apply is None:return self.m.release(self.r,"cron")
        return self.m.release(self.r,"coordinated-cron",runner=lambda _:apply(self.restart))
    def rc2(self):return self.m.release(self.r,"monitor",runner=self.monitor)

class Lifecycle:
    """Persistent supervisor receipt experiment, restricted to fixture root.

    A running service is expected to outlive a gate operation. Its lifetime
    receipt is separate from transaction receipts and cannot be auto-cleared
    by a successor supervisor. All operations must run in the same exclusive
    parent. The fixture accepts an argv for a synthetic service only.
    """
    def __init__(self,migration,argv,ready):
        from lock_migration import Migration
        require(isinstance(migration,Migration),"fixture required")
        self.m=migration
        self.argv=tuple(argv);self.ready=ready
        exe=Path(self.argv[0]).stat()
        self.exe_id=(exe.st_dev,exe.st_ino)
        self.path=migration.protected/"supervisor.json"
        self.owner=identity(os.getpid())
        self.child=None
    def _record(self,phase,child=None):
        from release_gate import atomic,encode
        atomic(self.path,encode({"phase":phase,"boot":self.owner.boot,
              "owner_pid":self.owner.pid,"owner_start":self.owner.start,
              "child_pid":None if child is None else child.pid,
              "child_start":None if child is None else child.start}),0o600)
    def start(self,timeout=2):
        require(identity(os.getpid())==self.owner,"supervisor identity changed")
        require(self.child is None and not os.path.lexists(self.path),"unresolved lifecycle; no adoption")
        self._record("starting")
        self.child=OwnedChild(self.argv)
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            try:
                i=identity(self.child.pid)
                if i.ppid==self.owner.pid and i.boot==self.owner.boot and (i.exe_dev,i.exe_ino)==self.exe_id and i.argv==tuple(os.fsencode(x) for x in self.argv) and self.ready(i.pid):
                    self.child_identity=i;self._record("running",i);return 0
            except (OSError,ValueError,Blocked):pass
            time.sleep(.02)
        # Keep the receipt on a failed or uncertain startup; no silent adoption.
        self.child.stop();raise Blocked("service readiness unproven")
    def healthy(self):
        try:return self.child is not None and not self.child.reaped and identity(self.child.pid)==self.child_identity and self.ready(self.child.pid)
        except (OSError,ValueError,AttributeError,Blocked):return False
    def stop(self):
        from release_gate import sync_dir
        require(identity(os.getpid())==self.owner and self.child is not None,"no owned child")
        require(not self.child.reaped,"unresolved child lifetime")
        self._record("stopping",self.child_identity)
        self.child.stop()
        require(self.child.reaped,"child termination unproven")
        self.child=None
        self.path.unlink();sync_dir(self.path.parent)
        return 0
    def restart(self):
        if self.child is not None:self.stop()
        return self.start()
