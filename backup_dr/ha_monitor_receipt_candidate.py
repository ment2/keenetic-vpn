#!/usr/bin/env python3
"""Offline replacement candidate for HA add-on monitor; no deployment here.
Uses existing HA agent child, public preflight, and receipt-only retry helper.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from ha_receipt_retry import ReceiptError, checked_file, deliver_pending

ROOT = Path('/data/ha-admin-agent')
URL = 'https://homeassistant-control-bridge.wlad124650.workers.dev'
INTERVAL = 30
CHILD_TIMEOUT = 80  # existing local child watchdog; remote exec cap remains 45
GOOD = {'HA_AGENT_IDLE','HA_AGENT_JOB_ACKNOWLEDGED','HA_AGENT_RESULT_DELIVERED'}
CLASSES = {'HTTPError','URLError','TimeoutError','AgentError'}
PREFLIGHT = 'HA_AGENT_PREFLIGHT_UNAVAILABLE:'
FAILED = 'HA_AGENT_STOPPED_FAIL_CLOSED:'


def state_write(root,status,detail='',polls=0):
    fd,tmp=tempfile.mkstemp(prefix='.monitor-state-',dir=root)
    try:
        os.fchmod(fd,0o600)
        with os.fdopen(fd,'w') as stream:
            json.dump(dict(status=status,detail=detail,polls=polls,updated_at=int(time.time()),pid=os.getpid()),stream)
            stream.flush(); os.fsync(stream.fileno())
        os.replace(tmp,root/'monitor-state.json')
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


def receipt_submit(job_id,payload):
    # Lazy import retains existing production API, token permissions and URL.
    # No claim, authorize, reconciliation, or execution endpoints here.
    import ha_bridge_tick as agent
    agent.preflight(URL)
    return agent.api('POST',URL+'/v1/agent/result/'+job_id,agent.read_token(),payload)


def child_tick(root):
    return subprocess.run([sys.executable,str(root/'ha_bridge_tick.py'),'--once','--url',URL],capture_output=True,text=True,timeout=CHILD_TIMEOUT)


def cycle(root,ordinary,submit,*,sleep=time.sleep):
    """One monitor cycle. Caller holds monitor.lock throughout.
    A saved receipt gets its own cycle; only no-journal permits a claim.
    Existing public preflight-only failure remains safe to retry next cycle.
    """
    if os.path.lexists(root/'monitor.stop'):
        return 'STOPPED','STOP_REQUESTED'
    result=deliver_pending(root,submit,sleep=sleep)
    if result=='RESULT_DELIVERED': return 'RUNNING','HA_AGENT_RESULT_DELIVERED'
    if result!='ABSENT': raise ReceiptError('UNEXPECTED_STATE')
    if os.path.lexists(root/'monitor.stop'): return 'STOPPED','STOP_REQUESTED'
    try:
        proc=ordinary(root)
    except Exception:
        proc=None
    # Child may have completed the operation and lost its ACK. Inspect only
    # after subprocess exits (or is killed/waited by subprocess.run timeout).
    result=deliver_pending(root,submit,sleep=sleep)
    if result=='RESULT_DELIVERED': return 'RUNNING','HA_AGENT_RESULT_DELIVERED'
    if result!='ABSENT': raise ReceiptError('UNEXPECTED_STATE')
    if proc is None: raise ReceiptError('TICK_FAILED_MANUAL_REVIEW')
    marker=proc.stdout.strip()
    if proc.returncode==0 and marker in GOOD: return 'RUNNING',marker
    if proc.returncode==4 and marker.startswith(PREFLIGHT) and marker[len(PREFLIGHT):] in CLASSES-{'AgentError'}:
        return 'DEGRADED','PREFLIGHT_UNAVAILABLE:'+marker[len(PREFLIGHT):]
    if marker.startswith(FAILED) and marker[len(FAILED):] in CLASSES:
        raise ReceiptError('TICK_FAILED_MANUAL_REVIEW:'+marker[len(FAILED):])
    raise ReceiptError('TICK_FAILED_MANUAL_REVIEW')


def run(root=ROOT,ordinary=child_tick,submit=receipt_submit,*,sleep=time.sleep):
    if root.is_symlink() or not root.is_dir(): return 3
    fd=checked_file(root/'monitor.lock',os.O_CREAT|os.O_RDWR)
    polls=0
    try:
        try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            print('MONITOR_ALREADY_RUNNING'); return 2
        # Like baseline, explicit start clears prior stop request; never journal.
        (root/'monitor.stop').unlink(missing_ok=True)
        state_write(root,'RUNNING')
        while True:
            status,detail=cycle(root,ordinary,submit,sleep=sleep)
            if status=='STOPPED':
                state_write(root,status,detail,polls); (root/'monitor.stop').unlink(missing_ok=True); return 0
            polls+=1; state_write(root,status,detail,polls)
            for _ in range(INTERVAL):
                if os.path.lexists(root/'monitor.stop') or os.path.lexists(root/'pending.json'): break
                sleep(1)
    except ReceiptError as exc:
        # Helper emits fixed, non-secret status codes only.
        state_write(root,'BLOCKED',str(exc),polls); return 3
    except Exception:
        state_write(root,'BLOCKED','UNEXPECTED_MONITOR_ERROR',polls); return 3
    finally: os.close(fd)


def start(root=ROOT):
    fd=checked_file(root/'monitor.lock',os.O_CREAT|os.O_RDWR)
    try:
        try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            print('MONITOR_ALREADY_RUNNING'); return 0
        # Release probe before spawning; run() acquires the exclusive lock.
        # A concurrent start can lose the race but cannot run a second loop.
        fcntl.flock(fd,fcntl.LOCK_UN)
        out=checked_file(root/'monitor.log',os.O_CREAT|os.O_WRONLY|os.O_APPEND)
        try:
            p=subprocess.Popen([sys.executable,__file__,'run'],stdin=subprocess.DEVNULL,stdout=out,stderr=out,close_fds=True,start_new_session=True)
        finally: os.close(out)
        print('MONITOR_LAUNCHED_PID:',p.pid); print('VERIFY_WITH_STATUS_AFTER_5_SECONDS'); return 0
    finally: os.close(fd)


def status(root=ROOT):
    fd=checked_file(root/'monitor.lock',os.O_CREAT|os.O_RDWR)
    locked=False
    try:
        try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: locked=True
    finally: os.close(fd)
    print('MONITOR_PROCESS:','RUNNING' if locked else 'NOT_RUNNING')
    print('PENDING_JOURNAL:',os.path.lexists(root/'pending.json'))
    try:
        with os.fdopen(checked_file(root/'monitor-state.json',os.O_RDONLY)) as f: d=json.load(f)
        for k in ('status','detail','polls','updated_at'): print(k.upper()+':',d.get(k))
    except FileNotFoundError: pass
    except Exception: print('STATE_UNREADABLE')
    return 0


def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('action',choices=['start','run','stop','status']); a=ap.parse_args()
    if ROOT.is_symlink() or not ROOT.is_dir(): return 3
    if a.action=='run': return run()
    if a.action=='start': return start()
    if a.action=='status': return status()
    fd=checked_file(ROOT/'monitor.stop',os.O_CREAT|os.O_WRONLY); os.close(fd); print('MONITOR_STOP_REQUESTED'); return 0

if __name__=='__main__': sys.exit(main())
