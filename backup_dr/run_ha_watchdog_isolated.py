#!/usr/bin/env python3
"""Local-only synthetic acceptance. Never imports the installed HA agent.
Run from a verified, private, extracted bundle: python3 -I -B run_ha_watchdog_isolated.py
This is an accidental-use guard, not an OS security sandbox.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import tempfile
import time
import unittest
import warnings

BASE = Path(__file__).resolve().parent
PRODUCTION = Path('/data/ha-admin-agent')
MODULES = {'ha_receipt_retry.py', 'ha_monitor_receipt_candidate.py',
           'ha_receipt_watchdog.py', 'ha_monitor_watchdog_candidate.py',
           'test_ha_receipt_watchdog.py', 'ha_bridge_tick.py',
           'run_ha_watchdog_isolated.py'}


def verify():
    if BASE == PRODUCTION or PRODUCTION in BASE.parents:
        raise RuntimeError('REFUSE_PRODUCTION_DIRECTORY')
    if BASE.stat().st_uid != os.geteuid() or stat.S_IMODE(BASE.stat().st_mode) & 0o077:
        raise RuntimeError('PRIVATE_DIRECTORY_REQUIRED')
    mf = BASE/'manifest.json'
    ms = mf.lstat()
    if not stat.S_ISREG(ms.st_mode) or ms.st_nlink != 1 or ms.st_uid != os.geteuid() or ms.st_mode & 0o022:
        raise RuntimeError('UNSAFE_MANIFEST')
    manifest = json.loads(mf.read_text())
    if set(manifest) != MODULES:
        raise RuntimeError('INVALID_MANIFEST')
    if {p.name for p in BASE.iterdir()} != MODULES | {'manifest.json'}:
        raise RuntimeError('UNEXPECTED_BUNDLE_CONTENTS')
    for name, digest in manifest.items():
        p = BASE/name
        s = p.lstat()
        if not stat.S_ISREG(s.st_mode) or s.st_nlink != 1 or s.st_uid != os.geteuid() or s.st_mode & 0o022:
            raise RuntimeError('UNSAFE_BUNDLE_FILE')
        if hashlib.sha256(p.read_bytes()).hexdigest() != digest:
            raise RuntimeError('BUNDLE_HASH_MISMATCH')


def install_guards():
    # Python-level guards protect this test process; reviewed synthetic child
    # snippets are restricted to the test suite. No live adapter in bundle.
    def guard(event,args):
        if event in ('socket.connect','socket.bind'):
            addr = args[1]
            if not isinstance(addr,tuple) or addr[0] != '127.0.0.1':
                raise RuntimeError('NON_LOOPBACK_NETWORK_REFUSED')
        elif event == 'socket.getaddrinfo':
            if args[0] not in ('127.0.0.1',None):
                raise RuntimeError('EXTERNAL_DNS_REFUSED')
        elif event == 'open':
            f = args[0]
            if isinstance(f,(str,bytes,os.PathLike)):
                # lexical comparison avoids recursively opening paths in hook
                p = os.path.abspath(os.fsdecode(f))
                if p == str(PRODUCTION) or p.startswith(str(PRODUCTION)+'/'):
                    raise RuntimeError('PRODUCTION_PATH_REFUSED')
        elif event == 'subprocess.Popen':
            exe,argv = args[:2]
            if exe != sys.executable or not isinstance(argv,(list,tuple)) or len(argv)!=4 or list(argv[:3]) != [sys.executable,'-S','-c']:
                # The actual tested fixture uses argv=[python,-S,-c,script].
                raise RuntimeError('NON_FIXTURE_SUBPROCESS_REFUSED')
    sys.addaudithook(guard)


def timing_test(root, w):
    """Use unchanged 13/45-second constants, never the live API."""
    from ha_receipt_retry import ReceiptError
    journal = root/'pending.json'
    data = dict(state='result_ready', job_id='11111111-1111-4111-8111-111111111111',
                lease_id='22222222-2222-4222-8222-222222222222',exit_code=0,output='SYNTHETIC_TIMING')
    journal.write_text(json.dumps(data)); journal.chmod(0o600)
    before=journal.read_bytes(); pids=root/'fixture-pids'; calls=[]
    def make(d):
        calls.append(d)
        script=f'import os,time; f=open({str(pids)!r},"a"); f.write(str(os.getpid())+"\\n"); f.close(); time.sleep(60)'
        return [sys.executable,'-S','-c',script]
    if (w.TOTAL,w.ATTEMPT,w.DELAYS,w.POLL)!=(45.0,13.0,(1.0,3.0),0.1):
        raise RuntimeError('UNEXPECTED_PRODUCTION_CONSTANTS')
    start=time.monotonic()
    try:
        w.deliver(root,make_command=make)
        raise RuntimeError('UNEXPECTED_TIMING_ACK')
    except ReceiptError as exc:
        if str(exc) not in ('RESULT_RETRY_EXHAUSTED','RESULT_DEADLINE_EXCEEDED'):
            raise
        outcome=str(exc)
    elapsed=time.monotonic()-start
    if journal.read_bytes()!=before or not calls or len(calls)>3 or len(set(calls))!=1:
        raise RuntimeError('TIMING_JOURNAL_OR_IDENTITY_CHANGED')
    ids=[int(p) for p in pids.read_text().splitlines()]
    if len(ids)!=len(calls): raise RuntimeError('TIMING_CHILD_START_UNVERIFIED')
    for pid in ids:
        try: os.kill(pid,0)
        except ProcessLookupError: pass
        else: raise RuntimeError('TIMING_CHILD_NOT_REAPED')
    if len(calls)!=3 or not 39.0<=elapsed<=45.5:
        raise RuntimeError('TIMING_ACCEPTANCE_LIMIT')
    print(f'ISOLATED_FULL_BUDGET_PASS attempts={len(calls)} elapsed={elapsed:.3f}s outcome={outcome} journal=unchanged children=reaped')
    return 0


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--timing',action='store_true',help='Run only the full default watchdog budget (~43 s), locally')
    args=ap.parse_args()
    verify()
    # no inherited proxy or Python search path; never load the active agent
    # from its own directory. -I recommended for caller as well.
    os.environ.clear()
    os.environ.update(PATH='/usr/bin:/bin',LANG='C.UTF-8',PYTHONPATH=str(BASE),PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1',NO_PROXY='127.0.0.1')
    sys.dont_write_bytecode = True
    sys.path.insert(0,str(BASE))
    os.chdir(BASE)
    warnings.simplefilter('always',ResourceWarning)
    with tempfile.TemporaryDirectory(prefix='ha-watchdog-fixture-') as tmp:
        old = tempfile.tempdir
        tempfile.tempdir = tmp
        os.environ.update(TMPDIR=tmp,HOME=tmp)
        try:
            install_guards()
            import ha_receipt_retry, ha_receipt_watchdog, ha_monitor_receipt_candidate, ha_monitor_watchdog_candidate
            import test_ha_receipt_watchdog as suite
            for mod in (ha_receipt_retry,ha_receipt_watchdog,ha_monitor_receipt_candidate,ha_monitor_watchdog_candidate,suite):
                if Path(mod.__file__).resolve().parent != BASE:
                    raise RuntimeError('UNEXPECTED_IMPORT_ORIGIN')
            if args.timing:
                return timing_test(Path(tmp),ha_receipt_watchdog)
            tests=unittest.defaultTestLoader.loadTestsFromModule(suite)
            if tests.countTestCases()!=18:
                raise RuntimeError('UNEXPECTED_TEST_COUNT')
            result=unittest.TextTestRunner(verbosity=2).run(tests)
            if not result.wasSuccessful(): return 1
            print('ISOLATED_WATCHDOG_ACCEPTANCE_PASS 18/18')
            return 0
        finally: tempfile.tempdir=old

if __name__=='__main__':
    sys.exit(main())
