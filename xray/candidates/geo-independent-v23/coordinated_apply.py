"""Disposable Python port of wrapper apply/rollback control flow.

No production entrypoint, no external command or service path. The caller
must enter the coordinated cron gate; restart is an in-process delegated
callback. SIGKILL leaves the outer durable receipt for inspection.
"""
from pathlib import Path
import os
import stat
from release_gate import atomic, sync_dir, require, decode

class Apply:
    def __init__(self,migration,generate,validate,health):
        from lock_migration import Migration
        require(isinstance(migration,Migration),"fixture required")
        self.m=migration
        self.root=migration.root/"opt/etc/xray"
        self.conf=self.root/"config.json"
        self.pending=self.root/"config.pending.json"
        self.backup=self.root/"config.lastgood.autoapply.json"
        self.generate=generate;self.validate=validate;self.health=health

    def read(self,p):
        fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
        with os.fdopen(fd,"rb") as f:
            s=os.fstat(f.fileno())
            require(stat.S_ISREG(s.st_mode) and s.st_uid==os.geteuid()
                    and s.st_nlink==1 and not s.st_mode&0o077,"unsafe config")
            return f.read()

    def remove_pending(self):
        if os.path.lexists(self.pending):
            self.read(self.pending)
            self.pending.unlink();sync_dir(self.root)

    def run(self,restart):
        # This is NOT a native authorization or handoff capability; the
        # fixture's outer Gate holds the lock for this entire callback.
        candidate=self.generate()
        if type(candidate) is not bytes or not candidate:return 1
        data=decode(candidate)
        if not isinstance(data,dict) or not any(isinstance(x,dict) and x.get("protocol")=="vless" for x in data.get("outbounds",[])):return 1
        if not self.validate(candidate):return 1
        old=self.read(self.conf)
        if old==candidate:
            self.remove_pending();return 0
        if not self.validate(old):return 1
        # Preserve existing wrapper's private candidate/lastgood semantics.
        for p in (self.pending,self.backup):
            if os.path.lexists(p):self.read(p)
        atomic(self.pending,candidate,0o600)
        atomic(self.backup,old,0o600)
        require(self.read(self.backup)==old and self.read(self.conf)==old,"config CAS")
        atomic(self.conf,candidate,0o600)
        try:
            if restart()==0 and self.health():
                require(self.read(self.conf)==candidate,"config changed during restart")
                self.remove_pending();return 0
        except Exception:
            pass
        # No guessing if a third-party writer changed the generation.
        require(self.read(self.conf)==candidate and self.read(self.backup)==old,"rollback CAS")
        atomic(self.conf,old,0o600)
        require(restart()==0 and self.health() and self.read(self.conf)==old,"rollback unverified")
        # Existing wrapper returns nonzero even on successful rollback;
        # outer release receipt therefore remains fenced.
        return 1
