"""Native Keenetic v23 adapter, review/check only.

No native mutating entrypoint. This module is deliberately safe to run on
the router with 'check': no lock creation, journal writes, service calls,
subscription requests, or cron changes. The executable transition remains
in release_gate.Gate's disposable implementation until separate approval.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import fcntl
import uuid
from release_gate import OLD_PINS,NEW_SHA,WRAPPER_SHA,NAMES,Blocked,require,sha,decode

OPT=Path("/opt")
PINS=OPT/"etc/vpn-monitor/dynamic-source-pins.json"
STATE=OPT/"etc/xray/v23-release-journal"
LOCK=OPT/"tmp/xray-update.lock"
STAGE=OPT/"var/lib/vpn-monitor/rc2-stage"
FULL=str(OPT/"var/lib/vpn-monitor/full-subscription.json")
PYTHON=str(OPT/"bin/python3")
BUILDER=OPT/"var/lib/vpn-monitor/geo-independent-v23-candidate.py"
BOOT=Path("/proc/sys/kernel/random/boot_id")
NEW_PINS=dict(OLD_PINS,**{NAMES[0]:NEW_SHA})

def read_regular(p,private=False,uid=0):
    fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,"rb") as f:
        s=os.fstat(f.fileno())
        require(stat.S_ISREG(s.st_mode) and s.st_uid==uid and s.st_nlink==1
                and not s.st_mode&(0o077 if private else 0o022),"unsafe file")
        return f.read()

def boot_id(p=BOOT):
    return str(uuid.UUID(p.read_text().strip()))

def safe_directory(p,uid=0,private=False):
    s=p.lstat()
    require(stat.S_ISDIR(s.st_mode) and s.st_uid==uid and not s.st_mode&(0o077 if private else 0o022),"unsafe directory")
    return s.st_dev,s.st_ino

def mount_record(path,mountinfo):
    """Longest containing mount; no raw device/path emitted in status."""
    path=str(Path(path))
    found=[]
    for l in mountinfo.splitlines():
        a=l.split()
        if "-" not in a or len(a)<10:continue
        pos=a.index("-")
        mount=re.sub(r"\\([0-7]{3})",lambda m:chr(int(m.group(1),8)),a[4])
        if path==mount or path.startswith(mount.rstrip("/")+"/"):
            found.append((len(mount),a[2],a[pos+1],a[5].split(","),a[pos+3].split(",")))
    require(bool(found),"mount absent")
    _,dev,fs,opts,superopts=max(found,key=lambda v:v[0])
    return {"device":dev,"fs":fs,"rw":"rw" in opts and "rw" in superopts}

def generation(up,pins):
    if sha(up)==OLD_PINS[NAMES[0]] and pins==OLD_PINS:return "old"
    if sha(up)==NEW_SHA and pins==NEW_PINS:return "new"
    return "unknown"

def boot_decision(*,current_boot,accepted_boot,receipt_present,journal_phase,pair,lock_exists,legacy_fenced):
    """Pure conservative startup admission; no automatic recovery on reboot."""
    if receipt_present:return "BLOCK_RECEIPT"
    if lock_exists is not True:return "BLOCK_MISSING_LOCK"
    try:
        valid_boot=type(current_boot) is str and type(accepted_boot) is str and str(uuid.UUID(current_boot))==current_boot and current_boot==accepted_boot
    except (ValueError,TypeError,AttributeError):valid_boot=False
    if not valid_boot:return "BLOCK_BOOT_REACCEPT"
    if legacy_fenced is not True:return "BLOCK_LEGACY"
    if journal_phase in ("prepared","rollback"):return "RECOVER_UNDER_LOCK"
    if journal_phase=="committed" and pair=="new":return "ALLOW_NEW"
    if journal_phase is None and pair=="old":return "ALLOW_OLD"
    return "BLOCK_GENERATION"

def rc2_commands(pins):
    require(pins in (OLD_PINS,NEW_PINS),"pins not reviewed")
    args=[a for name in NAMES for a in ("--source-sha",name+"="+pins[name])]
    return ([PYTHON,"-B","-m","monitoring.full_subscription_snapshot",*args],
            [PYTHON,"-B","-m","monitoring.rc2_snapshot","probe","--full",FULL,"--publish"])

def rc2_runner(pins,run):
    """Injected runner contract, used only by reviewed fixture/test adapter.

    Native caller must hold updater and monitor probe locks throughout.
    Never calls rc2_cycle's incompatible updater_idle() check while locked.
    """
    for argv in rc2_commands(pins):
        rc=run(argv,cwd=str(STAGE))
        if rc!=0:return rc
    return 0

def check():
    require(os.geteuid()==0,"root required")
    root=OPT.resolve(strict=True)
    opt_stat=OPT.lstat()
    require(opt_stat.st_uid==0,"opt owner")
    # Resolve only the /opt mount alias, reject aliases inside its tree.
    mount=mount_record(root,Path("/proc/self/mountinfo").read_text())
    require(mount["fs"]=="ext4" and mount["rw"],"persistent ext4 not confirmed")
    for rel in ("","bin","etc","etc/xray","etc/vpn-monitor","var","var/lib","var/lib/vpn-monitor"):
        dev,_=safe_directory(root/rel)
        require(dev==root.stat().st_dev,"unexpected mount inside persistent tree")
    # A 0600 file in a 0777 non-sticky directory can still be renamed or
    # removed by another user. Inode checks alone cannot close that race.
    lock_parent_dev,_=safe_directory(LOCK.parent)
    require(lock_parent_dev==root.stat().st_dev,"lock not on persistent mount")
    before=boot_id()
    fd=os.open(LOCK,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        s=os.fstat(fd)
        require(stat.S_ISREG(s.st_mode) and s.st_uid==0 and s.st_nlink==1 and not s.st_mode&0o077,"unsafe lock")
        fcntl.flock(fd,fcntl.LOCK_SH|fcntl.LOCK_NB)
        for n in NAMES[1:]:
            require(sha(read_regular(OPT/"bin"/n))==OLD_PINS[n],"dependency hash mismatch")
        require(sha(read_regular(OPT/"bin/xray-safe-hourly.sh"))==WRAPPER_SHA,"wrapper hash mismatch")
        pair=generation(read_regular(OPT/"bin"/NAMES[0]),decode(read_regular(PINS,True)))
        require(pair!="unknown","unknown pair")
        require(sha(read_regular(BUILDER))==NEW_SHA,"candidate SHA mismatch")
        compile(read_regular(BUILDER),"<reviewed updater>","exec")
        current=LOCK.lstat()
        require((s.st_dev,s.st_ino)==(current.st_dev,current.st_ino) and before==boot_id(),"boot or lock changed")
        print("NATIVE_CHECK",json.dumps({"filesystem":mount["fs"],"pair":pair,
             "candidate":"verified","journal_directory_present":os.path.lexists(STATE),
             "receipt_present":os.path.lexists(STATE/"run.json"),
             "boot_continuity":"same during check","release":"BLOCKED"},sort_keys=True))
    finally:os.close(fd)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("mode",choices=["check"])
    p.parse_args()
    try:check()
    except Exception as exc:
        # Fixed error class only, no exception path or configuration content.
        print("NATIVE_CHECK_BLOCKED",type(exc).__name__)
        raise SystemExit(1)

if __name__=="__main__":main()
