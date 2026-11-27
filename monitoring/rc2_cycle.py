"""RC2 monitor-only schedule, no production updater mutation."""
import argparse
import fcntl
import os
import sys
import time
from monitoring import dynamic_monitor_cycle as rc1


def run_module(name,args):
    if name=="monitoring.dynamic_snapshot":
        name="monitoring.rc2_snapshot"
    return rc1.run_module(name,args)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("mode",choices=["probe","publish"])
    a=p.parse_args()
    try:
        # Share the monitor-only lock with RC1: never run two candidates.
        with os.fdopen(os.open(rc1.BASE/("dynamic-"+a.mode+".lock"),
                              os.O_CREAT|os.O_RDWR,0o600),"r+") as lock:
            try:
                fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:
                print("RC2_SKIPPED lock_busy",flush=True)
                return
            rc=rc1.cycle(a.mode,runner=run_module)
            print("RC2_CYCLE",a.mode,rc,flush=True)
            raise SystemExit(rc)
    except Exception as exc:
        print("RC2_CYCLE_FAILED",a.mode,type(exc).__name__,flush=True)
        raise SystemExit(1)


if __name__=="__main__":
    main()
