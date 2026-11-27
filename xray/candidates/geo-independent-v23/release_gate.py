"""Review-only v23 release transaction and cron gate.

No live installation is authorized by this source. CLI permits only disposable
fixtures; native path/ownership/boot acceptance must precede a production entrypoint.
All cooperating operations share the existing updater lock inode.
"""
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile

NAMES=("xray-update-v23.py","setup_xray.py","xray_server_check.py","xray_openai_probe.py")
OLD_PINS=dict(zip(NAMES,(
 "00f08d13bd653ce72a57b0f73ec046f004dca1f900a36cfcec4d254dfa2392cf",
 "d949aedac4dda40ae75ceed32b14eaf1c74fccbc36916262eb7098ce6b40f265",
 "6d8c38107517dca8b6ecfaa0551f71d20897539b9a969ab95cf3d23dc4580c68",
 "1ca2484d5ec6ed4794ea980b07a3921eebd975b2875868b2430baa441a06e4b7")))
NEW_SHA="9e22a9b68a2e0fd5b1e66499778662419bc56cd8af491f229401269be2456ecd"
WRAPPER_SHA="c63c0f171cda5b5f3150731e0706784b66977b256d737856edfcce15fba223c8"

class Blocked(RuntimeError): pass
def require(ok,reason):
    if not ok: raise Blocked(reason)
def sha(b):return hashlib.sha256(b).hexdigest()
def encode(obj):return (json.dumps(obj,sort_keys=True,separators=(",",":"))+"\n").encode()
def decode(b):
    def unique(pairs):
        d={}
        for k,v in pairs:
            require(k not in d,"duplicate JSON key")
            d[k]=v
        return d
    return json.loads(b,object_pairs_hook=unique)

def sync_dir(p):
    fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)

def atomic(p,data,mode):
    fd,name=tempfile.mkstemp(prefix=".v23-",dir=p.parent)
    try:
        with os.fdopen(fd,"wb") as f:
            os.fchmod(f.fileno(),mode)
            f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(name,p);sync_dir(p.parent)
    finally:
        if os.path.exists(name):os.unlink(name)

class Gate:
    def __init__(self,root,old_pins,new_sha,wrapper_sha,*,cut=lambda _:None):
        self.root=Path(root).resolve()
        # Explicit fixture-only guard: no production invocation via this candidate.
        require(self.root.parent==Path(tempfile.gettempdir()).resolve()
                and self.root.name.startswith("v23-release-fixture-"),"disposable root required")
        require((self.root/"marker").read_bytes()==b"synthetic-only","fixture marker")
        self.uid=os.geteuid()
        self.bin=self.root/"opt/bin"
        self.up=self.bin/NAMES[0]
        self.pins=self.root/"opt/etc/vpn-monitor/dynamic-source-pins.json"
        self.lock=self.root/"opt/tmp/xray-update.lock"
        self.wrapper=self.bin/"xray-safe-hourly.sh"
        self.state=self.root/"opt/etc/xray/v23-release-journal"
        self.journal=self.state/"journal.json"
        self.receipt=self.state/"run.json"
        self.backup_up=self.state/"updater.before"
        self.backup_pins=self.state/"pins.before"
        self.old=dict(old_pins);self.new=dict(old_pins);self.new[NAMES[0]]=new_sha
        self.wrapper_sha=wrapper_sha;self.cut=cut
        require(set(self.old)==set(NAMES) and self.old[NAMES[0]]!=new_sha,"plan invalid")

    def read(self,p,private=False):
        fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
        with os.fdopen(fd,"rb") as f:
            st=os.fstat(f.fileno())
            require(stat.S_ISREG(st.st_mode) and st.st_uid==self.uid and st.st_nlink==1
                    and not st.st_mode & (0o077 if private else 0o022),"unsafe file")
            b=f.read()
        return b,stat.S_IMODE(st.st_mode)

    def exists(self,p):return os.path.lexists(p)

    @contextlib.contextmanager
    def held(self):
        st=self.state.lstat()
        require(stat.S_ISDIR(st.st_mode) and st.st_uid==self.uid and not st.st_mode&0o077,"unsafe journal directory")
        fd=os.open(self.lock,os.O_RDONLY|os.O_NOFOLLOW)
        try:
            s=os.fstat(fd)
            require(stat.S_ISREG(s.st_mode) and s.st_uid==self.uid and s.st_nlink==1 and not s.st_mode&0o077,"unsafe lock")
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            self.lock_id=(s.st_dev,s.st_ino)
            self.check_lock()
            yield
        finally:
            os.close(fd)

    def check_lock(self):
        s=self.lock.lstat()
        require((s.st_dev,s.st_ino)==self.lock_id and stat.S_ISREG(s.st_mode),"lock inode changed")

    def pair(self):
        return self.read(self.up),self.read(self.pins,True)

    def verify_dependencies(self):
        self.check_lock()
        require(sha(self.read(self.wrapper)[0])==self.wrapper_sha,"wrapper mismatch")
        for name in NAMES[1:]:
            require(sha(self.read(self.bin/name)[0])==self.old[name],"dependency mismatch")

    def pair_matches(self,expected):
        (u,_),(p,_)=self.pair()
        return sha(u)==expected[NAMES[0]] and decode(p)==expected

    def checked_journal(self):
        j=decode(self.read(self.journal,True)[0])
        require(isinstance(j,dict) and set(j)=={"phase","old_up","new_up","old_pin","new_pin","up_mode","pin_mode"},"journal schema")
        require(j["phase"] in ("prepared","committed","rollback") and j["old_up"]==self.old[NAMES[0]]
                and j["new_up"]==self.new[NAMES[0]] and j["new_pin"]==sha(encode(self.new)),"journal plan mismatch")
        require(type(j["up_mode"]) is int and 0<=j["up_mode"]<=0o777 and not j["up_mode"]&0o022
                and type(j["pin_mode"]) is int and 0<=j["pin_mode"]<=0o700 and not j["pin_mode"]&0o077,"journal modes")
        ub,_=self.read(self.backup_up,True);pb,_=self.read(self.backup_pins,True)
        require(sha(ub)==j["old_up"] and sha(pb)==j["old_pin"] and decode(pb)==self.old,"backup mismatch")
        (u,um),(p,pm)=self.pair()
        require(sha(u) in (j["old_up"],j["new_up"]) and sha(p) in (j["old_pin"],j["new_pin"])
                and um==j["up_mode"] and pm==j["pin_mode"],"unknown pair or mode")
        return j,ub,pb

    def write_journal(self,j,phase):
        self.check_lock();atomic(self.journal,encode(dict(j,phase=phase)),0o600)
        self.cut(phase)

    def replace_checked(self,p,old,data,mode,private=False):
        self.check_lock()
        require(self.read(p,private)==(old,mode),"CAS mismatch")
        atomic(p,data,mode)
        require(self.read(p,private)==(data,mode),"readback mismatch")

    def verify_idle(self):
        self.verify_dependencies()
        require(not self.exists(self.receipt),"ambiguous previous wrapper lifetime; inspect manually")

    def install(self,candidate):
        with self.held():
            self.verify_idle()
            require(not self.exists(self.journal) and self.pair_matches(self.old),"not old baseline")
            b=self.read(Path(candidate),True)[0]
            require(sha(b)==self.new[NAMES[0]],"candidate mismatch")
            compile(b,"<reviewed candidate>","exec")
            (u,um),(p,pm)=self.pair()
            j={"phase":"prepared","old_up":sha(u),"new_up":sha(b),"old_pin":sha(p),
               "new_pin":sha(encode(self.new)),"up_mode":um,"pin_mode":pm}
            atomic(self.backup_up,u,0o600);atomic(self.backup_pins,p,0o600)
            self.write_journal(j,"prepared")
            self.checked_journal()
            self.replace_checked(self.pins,p,encode(self.new),pm,True);self.cut("pins")
            self.replace_checked(self.up,u,b,um);self.cut("updater")
            self.verify_dependencies()
            require(self.pair_matches(self.new),"new pair mismatch")
            self.write_journal(j,"committed")

    def recover_locked(self,rollback=False):
        self.verify_idle()
        if not self.exists(self.journal):
            require(self.pair_matches(self.old),"unknown baseline")
            return "old"
        j,ub,pb=self.checked_journal()
        if j["phase"]=="committed" and not rollback:
            require(self.pair_matches(self.new),"committed pair mismatch")
            return "new"
        if j["phase"]=="committed":
            require(self.pair_matches(self.new),"committed pair mismatch")
            self.write_journal(j,"rollback")
        for path,prior,key,private in ((self.up,ub,"up_mode",False),(self.pins,pb,"pin_mode",True)):
            current,mode=self.read(path,private)
            require(mode==j[key] and sha(current) in ((j["old_up"],j["new_up"]) if not private else (j["old_pin"],j["new_pin"])),"rollback CAS mismatch")
            if current!=prior:self.replace_checked(path,current,prior,mode,private)
            self.cut("restore-"+("pins" if private else "updater"))
        require(self.pair_matches(self.old),"old pair mismatch")
        self.check_lock();self.journal.unlink();sync_dir(self.state)
        return "old"

    def recover(self,rollback=False):
        with self.held():return self.recover_locked(rollback)

    def cron(self):
        with self.held():
            generation=self.recover_locked()
            expected=self.new if generation=="new" else self.old
            require(self.pair_matches(expected),"pair mismatch")
            self.check_lock()
            # Durable intent survives death of this parent. Never auto-clear on
            # nonzero return, ambiguous child lifetime, reboot or exception.
            atomic(self.receipt,encode({"phase":"running","generation":generation,"pid":os.getpid()}),0o600)
            self.cut("before-wrapper")
            result=subprocess.run(["/bin/sh",str(self.wrapper)],close_fds=True)
            self.cut("after-wrapper")
            require(result.returncode==0,"wrapper nonzero; inspection required")
            self.verify_dependencies()
            require(self.pair_matches(expected),"pair changed during wrapper")
            self.check_lock();self.receipt.unlink();sync_dir(self.state)
            return generation
