"""Disposable migration of one flock inode. No live entrypoint.

Cooperating actors must already be gated and old descendants independently
drained before bootstrap. This cannot fence arbitrary privileged writers.
Never create a replacement lock after an ambiguous move or reboot.
"""
import contextlib
import ctypes
import fcntl
import json
import os
from pathlib import Path
import stat
import tempfile
import uuid
from release_gate import atomic, sync_dir, encode, decode, sha, require, Blocked

ACTORS=("cron","manual-updater","watchdog","S97","S98","legacy-vless","legacy-openai","RC2-probe")
# Synthetic contracts only; not hashes of installed legacy scripts.
GATED={a:sha(("gated-fixture:"+a).encode()) for a in ACTORS}

def rename_noreplace(src,dst):
    # Linux CI primitive: refuse to clobber any destination, even if it
    # appeared after the preflight. Native kernel/libc support is a gate.
    libc=ctypes.CDLL(None,use_errno=True)
    fn=getattr(libc,"renameat2",None)
    require(fn is not None,"renameat2 unavailable")
    fn.argtypes=(ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint)
    fn.restype=ctypes.c_int
    if fn(-100,os.fsencode(src),-100,os.fsencode(dst),1)!=0:
        n=ctypes.get_errno()
        raise OSError(n,os.strerror(n))

def valid_boot(b):
    try:return type(b) is str and str(uuid.UUID(b))==b
    except (ValueError,TypeError,AttributeError):return False

class Migration:
    def __init__(self,root,boot,*,cut=lambda _:None):
        self.root=Path(root).resolve()
        require(self.root.parent==Path(tempfile.gettempdir()).resolve()
                and self.root.name.startswith(("v23-lock-fixture-","v23-release-fixture-")),"fixture only")
        require((self.root/"marker").read_bytes()==b"synthetic-only","fixture marker")
        require(valid_boot(boot),"invalid boot")
        self.boot=boot;self.cut=cut;self.uid=os.geteuid()
        self.old=self.root/"opt/tmp/xray-update.lock"
        self.protected=self.root/"opt/etc/xray/locks"
        self.new=self.protected/"xray-update.lock"
        self.control=self.protected/"migration.lock"
        self.record=self.protected/"migration.json"
        self.receipt=self.protected/"actor-running.json"
        self.actors=self.root/"actors"
        self.release_state=self.root/"opt/etc/xray/v23-release-journal"
        self.release_receipt=self.release_state/"run.json"
        self.release_journal=self.release_state/"journal.json"

    def read(self,p):
        fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
        with os.fdopen(fd,"rb") as f:
            s=os.fstat(f.fileno())
            require(stat.S_ISREG(s.st_mode) and s.st_uid==self.uid
                    and s.st_nlink==1 and not s.st_mode&0o077,"unsafe file")
            return f.read()

    def exists(self,p):return os.path.lexists(p)

    def verify_dirs(self):
        for p in (self.root,self.root/"opt",self.root/"opt/etc",self.root/"opt/etc/xray",self.protected,self.actors):
            s=p.lstat()
            require(stat.S_ISDIR(s.st_mode) and s.st_uid==self.uid and not s.st_mode&0o022,"unsafe protected directory")
        require(not self.protected.stat().st_mode&0o077,"private lock directory required")
        s=self.old.parent.lstat()
        require(stat.S_ISDIR(s.st_mode) and s.st_uid==self.uid,"unexpected legacy parent")
        require(s.st_dev==self.protected.stat().st_dev,"cross device move")

    def verify_actors(self):
        require(set(p.name for p in self.actors.iterdir())==set(ACTORS),"actor inventory changed")
        for a in ACTORS:require(sha(self.read(self.actors/a))==GATED[a],"actor not gated")

    def identity(self,p):
        s=p.lstat()
        require(stat.S_ISREG(s.st_mode) and s.st_uid==self.uid and s.st_nlink==1
                and stat.S_IMODE(s.st_mode)==0o600,"unsafe lock")
        return [s.st_dev,s.st_ino]

    @contextlib.contextmanager
    def locked(self,p,expected=None):
        fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
        try:
            s=os.fstat(fd);ident=[s.st_dev,s.st_ino]
            require(stat.S_ISREG(s.st_mode) and s.st_uid==self.uid and s.st_nlink==1
                    and stat.S_IMODE(s.st_mode)==0o600,"unsafe fd")
            if expected is not None:require(ident==expected,"lock identity mismatch")
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            require(self.identity(p)==ident,"lock path changed")
            yield ident
        finally:os.close(fd)

    @contextlib.contextmanager
    def serialized(self):
        self.verify_dirs()
        with self.locked(self.control):
            self.verify_actors()
            require(not self.exists(self.receipt) and not self.exists(self.release_receipt),"ambiguous actor lifetime")
            yield

    def state(self):
        d=decode(self.read(self.record))
        require(isinstance(d,dict) and set(d)=={"phase","boot","inode","actors"}
                and d["phase"] in ("legacy","prepared","protected","rollback")
                and valid_boot(d["boot"]) and d["actors"]==GATED
                and isinstance(d["inode"],list) and len(d["inode"])==2
                and all(type(x) is int and x>0 for x in d["inode"]),"bad migration state")
        return d

    def save(self,d,phase):
        d=dict(d,phase=phase)
        atomic(self.record,encode(d),0o600)
        self.cut(phase)
        return d

    def sole(self,d):
        old,new=self.exists(self.old),self.exists(self.new)
        require(old!=new,"both or neither lock paths exist")
        p=self.old if old else self.new
        require(self.identity(p)==d["inode"],"lock replaced")
        return p

    def initialize(self,drained):
        # Drained is a fixture assertion, NOT a native process witness.
        with self.serialized():
            require(drained is True and not self.exists(self.record) and not self.exists(self.new),"bootstrap not accepted")
            with self.locked(self.old) as ident:
                self.save({"boot":self.boot,"inode":ident,"actors":GATED},"legacy")

    def move(self,src,dst,d):
        require(self.sole(d)==src and not self.exists(dst),"move CAS")
        # No copy, create, unlink, or hardlink. Same inode under flock.
        rename_noreplace(src,dst)
        sync_dir(src.parent);sync_dir(dst.parent)
        require(self.sole(d)==dst,"move readback")
        self.cut("renamed")

    def migrate(self):
        with self.serialized():
            d=self.state()
            require(d["boot"]==self.boot and d["phase"]=="legacy" and self.sole(d)==self.old,"legacy baseline not accepted")
            with self.locked(self.old,d["inode"]):
                d=self.save(d,"prepared")
                self.move(self.old,self.new,d)
                self.save(d,"protected")

    def recover(self,*,reaccept=False,drained=False):
        with self.serialized():
            d=self.state()
            if d["boot"]!=self.boot:
                require(reaccept is True and drained is True,"new boot requires explicit fixture reacceptance")
            p=self.sole(d)
            with self.locked(p,d["inode"]):
                if d["phase"]=="prepared":
                    # Uncommitted migration rolls back to original inode/path.
                    if p==self.new:self.move(self.new,self.old,d)
                    d=self.save(dict(d,boot=self.boot),"legacy")
                elif d["phase"]=="rollback":
                    if p==self.new:self.move(self.new,self.old,d)
                    d=self.save(dict(d,boot=self.boot),"legacy")
                else:
                    require(p==(self.new if d["phase"]=="protected" else self.old),"phase/path mismatch")
                    if d["boot"]!=self.boot:d=self.save(dict(d,boot=self.boot),d["phase"])
                return d["phase"]

    def rollback(self):
        with self.serialized():
            require(not self.exists(self.release_journal),"restore updater/pins before lock rollback")
            d=self.state()
            require(d["boot"]==self.boot and d["phase"]=="protected" and self.sole(d)==self.new,"not committed")
            with self.locked(self.new,d["inode"]):
                d=self.save(d,"rollback")
                self.move(self.new,self.old,d)
                self.save(d,"legacy")

    def run(self,actor,fn,*,gate=None):
        require(actor in ACTORS,"unknown actor")
        with self.serialized():
            require(gate is not None or not self.exists(self.release_journal),"use integrated release admission when journal exists")
            d=self.state()
            require(d["boot"]==self.boot and d["phase"] in ("legacy","protected"),"recovery required")
            p=self.sole(d)
            require(p==(self.new if d["phase"]=="protected" else self.old),"phase/path mismatch")
            with self.locked(p,d["inode"]):
                require(self.sole(d)==p,"lock path changed")
                if gate is not None:
                    require(gate.root==self.root and gate.state==self.release_state,"foreign release gate")
                    gate.lock=p;gate.lock_id=tuple(d["inode"])
                    gate.verify_idle()
                    if self.exists(self.release_journal):
                        j,_,_=gate.checked_journal()
                        require(j["phase"]=="committed" and gate.pair_matches(gate.new),"release not committed")
                    else:require(gate.pair_matches(gate.old),"unknown release baseline")
                atomic(self.receipt,encode({"actor":actor,"boot":self.boot,"pid":os.getpid(),"inode":d["inode"]}),0o600)
                self.cut("before-actor")
                rc=fn(p)
                self.cut("after-actor")
                require(type(rc) is int and rc==0,"actor completion unknown")
                self.verify_actors()
                if gate is not None:
                    gate.verify_idle()
                    require(gate.pair_matches(gate.new if self.exists(self.release_journal) else gate.old),"release pair changed")
                require(self.state()==d and self.sole(d)==p,"state changed during actor")
                self.receipt.unlink();sync_dir(self.protected)
                return d["phase"]

    def release(self,gate,operation,*,candidate=None,runner=None):
        """Fixture integration with the existing release gate.

        Control lock held first; release Gate alone acquires the data lock.
        Avoid nested same-inode flock. No CLI, no native production paths.
        Wrapper-owned S97 is part of the one guarded operation, not a
        second top-level actor invocation.
        """
        require(gate.root==self.root and gate.state==self.release_state,"foreign release gate")
        require(operation in ("install","cron","monitor","recover","rollback"),"unknown operation")
        with self.serialized():
            d=self.state()
            require(d["boot"]==self.boot and d["phase"]=="protected" and self.sole(d)==self.new,"protected lock required")
            gate.lock=self.new
            # Existing release Gate checks identity on open/readback. The
            # coordinator holds the control lock for the entire call.
            if operation=="install":result=gate.install(candidate)
            elif operation=="cron":result=gate.cron()
            elif operation=="monitor":result=gate.monitor_probe(runner)
            else:result=gate.recover(operation=="rollback")
            require(self.state()==d and self.sole(d)==self.new,"migration changed during release")
            return result
