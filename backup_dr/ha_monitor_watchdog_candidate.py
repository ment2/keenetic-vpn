#!/usr/bin/env python3
"""Offline HA monitor candidate: isolate receipt-only IO with a watchdog."""
import argparse
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import time
from ha_receipt_retry import ReceiptError, checked_file
from ha_receipt_watchdog import deliver
from ha_monitor_receipt_candidate import ROOT, URL, INTERVAL, GOOD, CLASSES, PREFLIGHT, FAILED, state_write, status

# 12 preflight + 3*20 claim/authorize/result + 45 command = 117 s nominal.
# 18 s margin; this is a LOCAL wrapper watchdog, not the remote exec limit.
CHILD_TIMEOUT=135
REMOTE_COMMAND_MAX=45
NOMINAL_CHILD_BUDGET=12+3*20+REMOTE_COMMAND_MAX


def child_tick(root):
    return subprocess.run([sys.executable,str(root/'ha_bridge_tick.py'),'--once','--url',URL],capture_output=True,text=True,timeout=CHILD_TIMEOUT)


def receipt_cycle(root,delivery):
    try: result=delivery(root)
    except ReceiptError as exc:
        if str(exc)=='STOP_REQUESTED_RECEIPT_RETAINED':
            return 'STOPPED','RECEIPT_RETAINED'
        raise
    if result=='RESULT_DELIVERED': return 'RUNNING','HA_AGENT_RESULT_DELIVERED'
    if result!='ABSENT': raise ReceiptError('UNEXPECTED_STATE')
    return None


def cycle(root,ordinary=child_tick,delivery=deliver):
    # Validate any journal before honoring a stop. A claimed journal is not
    # a clean stop; it requires manual review. A receipt-only stop retains it.
    result=receipt_cycle(root,delivery)
    if result: return result
    if os.path.lexists(root/'monitor.stop'): return 'STOPPED','STOP_REQUESTED'
    try: proc=ordinary(root)
    except Exception: proc=None
    # Do not interrupt ordinary execution on stop request. Wait for child
    # exit/watchdog; if uncertain, keep journal and block, never replay.
    result=receipt_cycle(root,delivery)
    if result: return result
    if proc is None: raise ReceiptError('TICK_FAILED_MANUAL_REVIEW')
    marker=proc.stdout.strip()
    if proc.returncode==0 and marker in GOOD:
        return 'RUNNING',marker
    if proc.returncode==4 and marker.startswith(PREFLIGHT) and marker[len(PREFLIGHT):] in CLASSES-{'AgentError'}:
        return 'DEGRADED','PREFLIGHT_UNAVAILABLE:'+marker[len(PREFLIGHT):]
    if marker.startswith(FAILED) and marker[len(FAILED):] in CLASSES:
        raise ReceiptError('TICK_FAILED_MANUAL_REVIEW:'+marker[len(FAILED):])
    raise ReceiptError('TICK_FAILED_MANUAL_REVIEW')


def run(root=ROOT,ordinary=child_tick,delivery=deliver,*,sleep=time.sleep):
    if root.is_symlink() or not root.is_dir(): return 3
    fd=checked_file(root/'monitor.lock',os.O_CREAT|os.O_RDWR); polls=0
    try:
        try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: print('MONITOR_ALREADY_RUNNING'); return 2
        (root/'monitor.stop').unlink(missing_ok=True)
        state_write(root,'RUNNING')
        while True:
            state,detail=cycle(root,ordinary,delivery)
            if state=='STOPPED':
                state_write(root,state,detail,polls)
                (root/'monitor.stop').unlink(missing_ok=True); return 0
            polls+=1; state_write(root,state,detail,polls)
            for _ in range(INTERVAL):
                if os.path.lexists(root/'monitor.stop') or os.path.lexists(root/'pending.json'): break
                sleep(1)
    except ReceiptError as exc:
        state_write(root,'BLOCKED',str(exc),polls); return 3
    except Exception:
        state_write(root,'BLOCKED','UNEXPECTED_MONITOR_ERROR',polls); return 3
    finally: os.close(fd)


def start(root=ROOT):
    fd=checked_file(root/'monitor.lock',os.O_CREAT|os.O_RDWR)
    try:
        try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: print('MONITOR_ALREADY_RUNNING'); return 0
        fcntl.flock(fd,fcntl.LOCK_UN)
        out=checked_file(root/'monitor.log',os.O_CREAT|os.O_WRONLY|os.O_APPEND)
        try:
            p=subprocess.Popen([sys.executable,'-B',__file__,'run'],stdin=subprocess.DEVNULL,stdout=out,stderr=out,close_fds=True,start_new_session=True)
        finally: os.close(out)
        print('MONITOR_LAUNCHED_PID:',p.pid); print('VERIFY_WITH_STATUS_AFTER_5_SECONDS'); return 0
    finally: os.close(fd)


def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('action',choices=['start','run','stop','status']); a=ap.parse_args()
    if ROOT.is_symlink() or not ROOT.is_dir(): return 3
    if a.action=='run': return run()
    if a.action=='start': return start()
    if a.action=='status': return status()
    fd=checked_file(ROOT/'monitor.stop',os.O_CREAT|os.O_WRONLY); os.close(fd); print('MONITOR_STOP_REQUESTED'); return 0

if __name__=='__main__': sys.exit(main())
