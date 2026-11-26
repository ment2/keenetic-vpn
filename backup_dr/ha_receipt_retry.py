"""Offline candidate: retry only an existing HA result_ready journal.

Caller is the local monitor, holding monitor.lock. No queue claim, execution,
permission changes, or token handling here. Inject the existing result API.
"""
import contextlib
import errno
import fcntl
import http.client
import json
import os
import re
import socket
import ssl
import stat
import time
import urllib.error
from pathlib import Path

UUID = re.compile(r'[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}', re.I)
MAX_JOURNAL = 100000
MAX_OUTPUT = 16000
DELAYS = (1, 3)  # 3 attempts total; then manual review, no busy loop
RETRY_HTTP = {502, 503, 504}
TRANSIENT_ERRNO = {errno.ECONNRESET, errno.ECONNREFUSED, errno.ETIMEDOUT,
                   errno.EPIPE, errno.ENETUNREACH, errno.EHOSTUNREACH}

class ReceiptError(Exception):
    """Redacted, stable status only."""


def transient(exc):
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code in RETRY_HTTP
    if isinstance(exc, urllib.error.URLError):
        exc = exc.reason
    if isinstance(exc, ssl.SSLError):
        return False
    if isinstance(exc, socket.gaierror):
        return exc.errno == socket.EAI_AGAIN
    return isinstance(exc, (TimeoutError, http.client.RemoteDisconnected)) or (isinstance(exc, OSError) and exc.errno in TRANSIENT_ERRNO)


def checked_file(path, flags):
    fd = os.open(path, flags | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    s = os.fstat(fd)
    if not stat.S_ISREG(s.st_mode) or s.st_mode & 0o077 or s.st_uid != os.geteuid() or s.st_nlink != 1:
        os.close(fd)
        raise ReceiptError('UNSAFE_LOCAL_FILE')
    return fd


@contextlib.contextmanager
def agent_lock(root):
    if root.is_symlink() or not root.is_dir():
        raise ReceiptError('INVALID_ROOT')
    fd = checked_file(root/'agent.lock', os.O_CREAT | os.O_RDWR)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ReceiptError('AGENT_BUSY') from None
        yield
    finally:
        os.close(fd)


def record(path):
    def strict_pairs(pairs):
        d = {}
        for k, v in pairs:
            if k in d:
                raise ValueError('duplicate key')
            d[k] = v
        return d
    try:
        with os.fdopen(checked_file(path, os.O_RDONLY), 'rb') as f:
            s = os.fstat(f.fileno())
            raw = f.read(MAX_JOURNAL+1)
        if len(raw) > MAX_JOURNAL:
            raise ReceiptError('JOURNAL_TOO_LARGE')
        j = json.loads(raw, object_pairs_hook=strict_pairs)
    except (OSError, ValueError, UnicodeError, RecursionError):
        raise ReceiptError('JOURNAL_UNREADABLE') from None
    if not isinstance(j, dict) or j.get('state') != 'result_ready':
        raise ReceiptError('JOURNAL_REQUIRES_MANUAL_REVIEW')
    if set(j) != {'state','job_id','lease_id','exit_code','output'}:
        raise ReceiptError('INVALID_JOURNAL_SCHEMA')
    if any(not isinstance(j[k],str) or not UUID.fullmatch(j[k]) for k in ('job_id','lease_id')):
        raise ReceiptError('INVALID_JOURNAL_IDENTITY')
    if type(j['exit_code']) is not int or not -1000 <= j['exit_code'] <= 1000 or not isinstance(j['output'],str) or len(j['output'].encode('utf-16-le',errors='surrogatepass'))//2 > MAX_OUTPUT:
        raise ReceiptError('INVALID_RESULT')
    try:
        payload = {k:j[k] for k in ('lease_id','exit_code','output')}
        if len(json.dumps(payload,ensure_ascii=True).encode()) > MAX_JOURNAL:
            raise ReceiptError('RESULT_TOO_LARGE')
        j['output'].encode('utf-8')
    except UnicodeError:
        raise ReceiptError('INVALID_RESULT_ENCODING') from None
    return (s.st_dev,s.st_ino,raw),j


def deliver_pending(root, submit, *, sleep=time.sleep):
    """Monitor hook: invoke before any claim, with monitor.lock held.

    submit(job_id, payload) is the existing authenticated result API only;
    it must have a finite network timeout (<= 20s). No fallback endpoint.
    Caller must stop on ReceiptError; only ABSENT allows an ordinary tick.
    DELIVERED means this tick handled receipt only; next tick may claim.
    """
    root = Path(root)
    path = root/'pending.json'
    with agent_lock(root):
        if not os.path.lexists(path):
            return 'ABSENT'
        identity,j = record(path)
        for attempt in range(len(DELAYS)+1):
            if record(path)[0] != identity:
                raise ReceiptError('JOURNAL_CHANGED')
            payload = {k:j[k] for k in ('lease_id','exit_code','output')}
            try:
                ack = submit(j['job_id'],payload)
            except Exception as e:
                if not transient(e):
                    raise ReceiptError('RESULT_DELIVERY_REJECTED') from None
                if attempt == len(DELAYS):
                    raise ReceiptError('RESULT_RETRY_EXHAUSTED') from None
                sleep(DELAYS[attempt])
                continue
            if not isinstance(ack,dict) or ack.get('ok') is not True:
                raise ReceiptError('RESULT_ACK_INVALID')
            if record(path)[0] != identity:
                raise ReceiptError('JOURNAL_CHANGED_AFTER_ACK')
            path.unlink()
            fd=os.open(root,os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
            return 'RESULT_DELIVERED'
    raise ReceiptError('UNEXPECTED_STATE')


def monitor_cycle(root, submit, ordinary_tick, *, sleep=time.sleep):
    """Candidate replacement for one monitor iteration under monitor.lock.

    ordinary_tick must be the existing bounded agent child (owns agent.lock).
    It returns True only for a valid acknowledged/idle outcome; otherwise
    False. Exceptions and failures without a journal stop the monitor.
    No normal tick occurs in the same cycle as a pending result delivery.
    """
    result=deliver_pending(root,submit,sleep=sleep)
    if result != 'ABSENT':
        return result
    try:
        ok=ordinary_tick()
    except Exception:
        ok=False
    # An ambiguous failed claim with no journal remains fail-closed. A child
    # may have persisted a result immediately before its transport failed.
    result=deliver_pending(root,submit,sleep=sleep)
    if result != 'ABSENT':
        return result
    if ok is not True:
        raise ReceiptError('TICK_FAILED_MANUAL_REVIEW')
    return 'TICK_ACKNOWLEDGED'
