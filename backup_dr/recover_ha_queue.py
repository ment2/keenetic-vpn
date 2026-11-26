#!/usr/bin/env python3
"""Owner-local HA queue recovery. Never run reset through the HA MCP queue."""
import argparse
import contextlib
import fcntl
import re
import json
import os
import stat
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path('/data/ha-admin-agent')
BASE = 'https://homeassistant-control-bridge.wlad124650.workers.dev'
UUID = re.compile(r"[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}", re.I)
SCOPES = {'diagnostic', 'exec', 'read_file', 'write_file'}

class RecoveryError(Exception):
    pass

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

def token(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as f:
        s = os.fstat(f.fileno())
        if not stat.S_ISREG(s.st_mode) or s.st_mode & 0o077 or s.st_uid != os.geteuid():
            raise RecoveryError('INSECURE_TOKEN_FILE')
        value = f.read(1025).strip().decode('ascii')
    if not 32 <= len(value) <= 1024 or any(not 33 <= ord(c) <= 126 for c in value):
        raise RecoveryError('INVALID_TOKEN_FILE')
    return value

class Client:
    def __init__(self, admin):
        self.admin = admin
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    def call(self, path, data=None, policy=None):
        headers = {'Authorization': 'Bearer '+self.admin, 'User-Agent': 'ha-control-agent/0.1-candidate', 'Accept': 'application/json'}
        if policy is not None:
            headers['x-control-policy-token'] = policy
        body = None if data is None else json.dumps(data).encode()
        if body is not None:
            headers['Content-Type'] = 'application/json'
        try:
            with self.opener.open(urllib.request.Request(BASE+path, data=body, headers=headers), timeout=15) as response:
                raw = response.read(262145)
                if len(raw)>262144:
                    raise RecoveryError('RESPONSE_TOO_LARGE')
                return json.loads(raw)
        except urllib.error.HTTPError as e:
            marker = '_CF_1010' if e.code == 403 and re.search(rb'(?:Error|error code:)\s*1010\b', e.read(4096), re.I) else ''
            raise RecoveryError(('GET' if body is None else 'POST')+'_HTTP_'+str(e.code)+marker) from None
        except (OSError, ValueError):
            raise RecoveryError(('GET' if body is None else 'POST')+'_TRANSPORT_OR_JSON_ERROR') from None

def state(client):
    p = client.call('/v1/permissions')
    if not isinstance(p, dict) or type(p.get('revision')) is not int or p.get('authority') != 'durable_object' or p.get('remote_enabled') is not True or p.get('owner_admin_enabled') is not True or not isinstance(p.get('scopes'),list) or any(type(x) is not str for x in p['scopes']) or set(p['scopes']) != SCOPES:
        raise RecoveryError('UNEXPECTED_POLICY_NO_CHANGE')
    return p

def guard(client, root):
    if os.path.lexists(root/'pending.json'):
        raise RecoveryError('PENDING_JOURNAL_PRESENT_NO_CHANGE')
    # Audit is a bounded history, not an atomic queue lock. Fail closed if a
    # visible claim has no subsequent terminal event; do not reconcile unknowns.
    a = client.call('/v1/audit')
    if not isinstance(a,dict) or not isinstance(a.get('events'),list):
        raise RecoveryError('AUDIT_UNAVAILABLE_NO_CHANGE')
    latest = {}
    for e in a['events']:
        if not isinstance(e,dict):
            raise RecoveryError('INVALID_AUDIT_NO_CHANGE')
        j = e.get('job_id')
        if j and e.get('event') in ('claimed','lease_expired_unverified','result_received','manually_reconciled','blocked_job_resolved_by_result'):
            latest.setdefault(j,e['event'])
    if any(v in ('claimed','lease_expired_unverified') for v in latest.values()):
        raise RecoveryError('VISIBLE_RUNNING_OR_UNKNOWN_JOB_NO_CHANGE')
    if os.path.lexists(root/'pending.json'):
        raise RecoveryError('PENDING_JOURNAL_PRESENT_NO_CHANGE')

def recover(client, root, policy, expect):
    before = state(client)
    if before['revision'] != expect:
        raise RecoveryError('REVISION_CHANGED_NO_CHANGE')
    guard(client, root)
    if state(client) != before or os.path.lexists(root/'pending.json'):
        raise RecoveryError('STATE_CHANGED_NO_CHANGE')
    payload = {k:before[k] for k in ('remote_enabled','owner_admin_enabled','scopes')}
    try:
        ack = client.call('/v1/owner/permissions',payload,policy)
        if not isinstance(ack,dict) or ack.get('ok') is not True or ack.get('revision') != expect+1:
            raise RecoveryError('UNEXPECTED_ACK')
        after = state(client)
        if after['revision'] != expect+1 or any(after[k]!=v for k,v in payload.items()):
            raise RecoveryError('VERIFY_FAILED')
    except RecoveryError as e:
        raise RecoveryError(str(e)+'; CHECK_POLICY_AND_JOBS_BEFORE_ANY_RETRY') from None
    return after['revision']

@contextlib.contextmanager
def local_fence(root):
    # Hold both existing agent locks through the owner operation. Never remove
    # the pending journal or attempt to override a live agent.
    with contextlib.ExitStack() as stack:
        for name in ('monitor.lock','agent.lock'):
            fd=os.open(root/name,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK,0o600)
            stack.callback(os.close,fd)
            st=os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_uid!=os.geteuid() or st.st_mode & 0o077:
                raise RecoveryError('INSECURE_LOCK_FILE')
            try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError: raise RecoveryError('MONITOR_OR_AGENT_RUNNING_NO_CHANGE') from None
        if os.path.lexists(root/'pending.json'):
            raise RecoveryError('PENDING_JOURNAL_PRESENT_NO_CHANGE')
        yield

def recovery_status(client):
    r=client.call('/v1/recovery/status')
    if not isinstance(r,dict) or type(r.get('unresolved_count')) is not int or r['unresolved_count']<0 or type(r.get('generation')) is not int:
        raise RecoveryError('RECOVERY_STATUS_UNAVAILABLE_NO_CHANGE')
    return r

def reconcile(client,root,policy,job,expect):
    if not UUID.fullmatch(job): raise RecoveryError('INVALID_JOB_ID')
    before=state(client)
    if before['revision']!=expect: raise RecoveryError('REVISION_CHANGED_NO_CHANGE')
    if os.path.lexists(root/'pending.json'): raise RecoveryError('PENDING_JOURNAL_PRESENT_NO_CHANGE')
    r=recovery_status(client)
    if r['unresolved_count']!=1 or r.get('blocked_job')!=job:
        raise RecoveryError('NOT_SOLE_BLOCKED_JOB_NO_CHANGE')
    j=client.call('/v1/jobs/'+job)
    if not isinstance(j,dict) or j.get('id')!=job or j.get('status')!='unknown':
        raise RecoveryError('NOT_UNKNOWN_NO_CHANGE')
    if state(client)!=before or recovery_status(client)!=r or os.path.lexists(root/'pending.json'):
        raise RecoveryError('STATE_CHANGED_NO_CHANGE')
    try:
        ack=client.call('/v1/owner/reconcile',{'id':job,'action':'acknowledge_unknown_no_reexecute'},policy)
        if not isinstance(ack,dict) or ack.get('ok') is not True: raise RecoveryError('UNEXPECTED_ACK')
        after=client.call('/v1/jobs/'+job)
        rs=recovery_status(client)
        if after.get('id')!=job or after.get('status')!='failed' or rs['unresolved_count']!=0 or rs.get('blocked_job') is not None or state(client)!=before:
            raise RecoveryError('VERIFY_FAILED')
    except RecoveryError as e:
        raise RecoveryError(str(e)+'; CHECK_POLICY_AND_JOBS_BEFORE_ANY_RETRY') from None
    return True

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    m=ap.add_mutually_exclusive_group()
    m.add_argument('--reset-queued',action='store_true',help='Cancel ALL queued HA jobs via same-policy revision bump')
    m.add_argument('--reconcile-unknown',metavar='JOB_ID',help='Acknowledge one reviewed UNKNOWN without re-execution')
    ap.add_argument('--expect-revision',type=int,help='Expected current revision; prevents replay after successful reset')
    args=ap.parse_args()
    try:
        if ROOT.is_symlink() or not ROOT.is_dir():
            raise RecoveryError('INVALID_AGENT_ROOT')
        c=Client(token(ROOT/'CONTROL_ADMIN_TOKEN'))
        before=state(c)
        print('AUTH_OK REVISION:',before['revision'],flush=True)
        if not args.reset_queued and not args.reconcile_unknown:
            print('READ_ONLY; PENDING_JOURNAL:',os.path.lexists(ROOT/'pending.json'))
            return 0
        if not sys.stdin.isatty():
            raise RecoveryError('LOCAL_INTERACTIVE_TERMINAL_REQUIRED')
        expect=before['revision'] if args.expect_revision is None else args.expect_revision
        if before['revision']!=expect:
            raise RecoveryError('REVISION_CHANGED_NO_CHANGE')
        policy=token(ROOT/'CONTROL_POLICY_TOKEN')
        if policy==c.admin:
            raise RecoveryError('CREDENTIALS_MUST_DIFFER')
        if args.reconcile_unknown:
            job=args.reconcile_unknown
            if not UUID.fullmatch(job): raise RecoveryError('INVALID_JOB_ID')
            phrase='RECONCILE '+job
            print('Review local effects and durable journal first. Never reexecute an uncertain operation.')
            if input('Acknowledge only reviewed UNKNOWN; type '+phrase+': ')!=phrase:
                raise RecoveryError('CANCELLED_NO_CHANGE')
            with local_fence(ROOT):
                reconcile(c,ROOT,policy,job,expect)
            print('UNKNOWN_RECONCILED_OK')
        else:
            if input('Cancel ALL queued HA jobs; type RESET '+str(expect)+': ') != 'RESET '+str(expect):
                raise RecoveryError('CANCELLED_NO_CHANGE')
            with local_fence(ROOT):
                if recovery_status(c)['unresolved_count']!=0:
                    raise RecoveryError('UNKNOWN_PRESENT_NO_CHANGE')
                print('QUEUE_RESET_ACK: True REVISION:',recover(c,ROOT,policy,expect))
        return 0
    except RecoveryError as e:
        print('RECOVERY_STOP:',str(e)); return 1
    except (OSError,UnicodeError,EOFError,KeyboardInterrupt):
        print('RECOVERY_STOP: LOCAL_IO_OR_INTERRUPTED; VERIFY_BEFORE_RETRY'); return 1

if __name__=='__main__':
    sys.exit(main())
