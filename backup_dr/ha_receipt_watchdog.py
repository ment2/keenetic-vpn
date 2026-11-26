"""Offline receipt-only watchdog candidate. Parent owns locks and journal.
Child can submit an existing receipt, but cannot claim jobs or remove journal.
"""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import time
from ha_receipt_retry import ReceiptError, agent_lock, record, transient

ROOT = Path('/data/ha-admin-agent')
URL = 'https://homeassistant-control-bridge.wlad124650.workers.dev'
TOTAL = 45.0
ATTEMPT = 13.0
DELAYS = (1.0, 3.0)
POLL = 0.1
ACK, RETRY, REJECT, BAD_ACK = 0, 10, 11, 12


def digest(identity):
    return hashlib.sha256(identity[2]).hexdigest()


def receipt_only(root, expected, submit):
    """No writes, no claims, no execution. Parent validates identity again."""
    try:
        identity, j = record(root/'pending.json')
        if digest(identity) != expected:
            return REJECT
        ack = submit(j['job_id'], {k:j[k] for k in ('lease_id','exit_code','output')})
    except Exception as exc:
        return RETRY if transient(exc) else REJECT
    return ACK if isinstance(ack,dict) and ack.get('ok') is True else BAD_ACK


def live_submit(job_id,payload):
    # Use the already deployed API, only this fixed endpoint and preflight.
    import ha_bridge_tick as agent
    agent.preflight(URL)
    return agent.api('POST',URL+'/v1/agent/result/'+job_id,agent.read_token(),payload)


def command(expected):
    return [sys.executable,'-B',str(Path(__file__).resolve()),'--submit-only',expected]


def stopped(root):
    return os.path.lexists(root/'monitor.stop')


def check(root,deadline):
    if stopped(root):
        raise ReceiptError('STOP_REQUESTED_RECEIPT_RETAINED')
    if time.monotonic() >= deadline:
        raise ReceiptError('RESULT_DEADLINE_EXCEEDED')


def attempt(root,argv,deadline):
    """Watchdog kills/reaps only receipt-only subprocess, never agent tick.
    No output pipe or sensitive arguments except a local journal digest.
    """
    check(root,deadline)
    end=min(deadline,time.monotonic()+ATTEMPT)
    with subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL,close_fds=True) as p:
        try:
            while True:
                check(root,deadline)
                remaining=end-time.monotonic()
                if remaining<=0:
                    return RETRY
                try:
                    rc=p.wait(timeout=min(POLL,remaining))
                except subprocess.TimeoutExpired:
                    continue
                check(root,deadline)
                return rc
        finally:
            if p.poll() is None:
                p.kill()
            p.wait()


def wait_delay(root,seconds,deadline):
    end=min(deadline,time.monotonic()+seconds)
    while True:
        check(root,deadline)
        remain=end-time.monotonic()
        if remain<=0: return
        time.sleep(min(POLL,remain))


def deliver(root,*,make_command=command):
    root=Path(root); path=root/'pending.json'
    with agent_lock(root):
        if not os.path.lexists(path): return 'ABSENT'
        identity,_=record(path)  # invalid/uncertain always fail closed
        deadline=time.monotonic()+TOTAL
        for i in range(len(DELAYS)+1):
            check(root,deadline)
            if record(path)[0]!=identity: raise ReceiptError('JOURNAL_CHANGED')
            rc=attempt(root,make_command(digest(identity)),deadline)
            if rc==ACK:
                check(root,deadline)
                if record(path)[0]!=identity: raise ReceiptError('JOURNAL_CHANGED_AFTER_ACK')
                path.unlink()
                fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
                try: os.fsync(fd)
                finally: os.close(fd)
                return 'RESULT_DELIVERED'
            if rc==BAD_ACK: raise ReceiptError('RESULT_ACK_INVALID')
            if rc!=RETRY: raise ReceiptError('RESULT_DELIVERY_REJECTED')
            if i==len(DELAYS): raise ReceiptError('RESULT_RETRY_EXHAUSTED')
            wait_delay(root,DELAYS[i],deadline)
    raise ReceiptError('UNEXPECTED_STATE')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--submit-only',required=True)
    a=p.parse_args()
    if len(a.submit_only)!=64 or any(c not in '0123456789abcdef' for c in a.submit_only): return REJECT
    return receipt_only(ROOT,a.submit_only,live_submit)

if __name__=='__main__': sys.exit(main())
