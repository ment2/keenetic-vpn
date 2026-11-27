"""Monitor-only cron entrypoint, staged until device acceptance.

Probe cycle: refresh full subscription and probe, every 15 minutes, offset
from the production updater. Publish cycle: read-only pool membership and
MQTT snapshot every minute. No production service/cron/firewall changes.
"""
import argparse
import fcntl
import json
import os
import re
import stat
import subprocess
import sys
import time
from pathlib import Path
from monitoring.full_subscription_snapshot import DEFAULT_OUTPUT, SOURCE_NAMES

BASE = Path("/opt/var/lib/vpn-monitor")
PINS = Path("/opt/etc/vpn-monitor/dynamic-source-pins.json")
UPDATE_LOCK = Path("/opt/tmp/xray-update.lock")
START_MINUTES = {3,18,33,48}


def source_pins(path=PINS):
    st=Path(path).lstat()
    if not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or st.st_mode & 0o077:
        raise ValueError("private source pin file required")
    with open(path) as f:
        data=json.load(f)
    if not isinstance(data,dict) or set(data)!=set(SOURCE_NAMES) or not all(
        isinstance(v,str) and re.fullmatch(r"[a-f0-9]{64}",v) for v in data.values()):
        raise ValueError("invalid source pins")
    return data


def updater_idle(path=UPDATE_LOCK):
    # Read-only observation of the existing lock, never create it or hold it
    # during network work. The probe processes remain independently isolated.
    try:
        with open(path,"rb") as f:
            try:
                fcntl.flock(f.fileno(),fcntl.LOCK_SH|fcntl.LOCK_NB)
            except BlockingIOError:
                return False
            finally:
                fcntl.flock(f.fileno(),fcntl.LOCK_UN)
        return True
    except OSError:
        return False


def run_module(name,args):
    # No shell interpolation, no raw subscription or secrets in argv.
    return subprocess.run([sys.executable,"-B","-m",name,*args],check=False).returncode


def cycle(mode, *, minute=None, pins_reader=source_pins, idle=updater_idle,
          runner=run_module):
    if mode=="publish":
        return runner("monitoring.dynamic_snapshot",["publish","--full",DEFAULT_OUTPUT,"--publish"])
    if mode!="probe":
        raise ValueError("unknown mode")
    if (time.localtime().tm_min if minute is None else minute) not in START_MINUTES:
        return 2
    if not idle():
        return 3
    pins=pins_reader()
    args=[a for name in SOURCE_NAMES for a in ("--source-sha",name+"="+pins[name])]
    rc=runner("monitoring.full_subscription_snapshot",args)
    if rc:
        return rc
    if not idle():
        return 3
    return runner("monitoring.dynamic_snapshot",["probe","--full",DEFAULT_OUTPUT,"--publish"])


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("mode",choices=["probe","publish"])
    a=parser.parse_args()
    try:
        with os.fdopen(os.open(BASE/("dynamic-"+a.mode+".lock"),
                              os.O_CREAT|os.O_RDWR,0o600),"r+") as lock:
            try:
                fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:
                print("MONITOR_SKIPPED lock_busy",flush=True)
                return
            rc=cycle(a.mode)
            print("MONITOR_CYCLE",a.mode,rc,flush=True)
            raise SystemExit(rc)
    except Exception as exc:
        print("MONITOR_FAILED",a.mode,type(exc).__name__,flush=True)
        raise SystemExit(1)


if __name__=="__main__":
    main()
