import json, os, subprocess, sys, tempfile, threading, time, unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
import ha_receipt_watchdog as w
import ha_monitor_watchdog_candidate as m
from ha_receipt_retry import ReceiptError, record

class WatchdogTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name); self.p=self.root/'pending.json'
        self.j=dict(state='result_ready',job_id='11111111-1111-4111-8111-111111111111',lease_id='22222222-2222-4222-8222-222222222222',exit_code=0,output='SYNTHETIC')
        self.write(); self.calls=[]
    def write(self):
        self.p.write_text(json.dumps(self.j)); self.p.chmod(0o600)
    def cmd(self,script):
        def f(d): self.calls.append(d); return [sys.executable,'-S','-c',script]
        return f
    def fast(self):
        return patch.multiple(w,TOTAL=4,ATTEMPT=.8,DELAYS=(.02,.04),POLL=.01)
    def test_ack(self):
        with self.fast(): self.assertEqual(w.deliver(self.root,make_command=self.cmd('raise SystemExit(0)')),'RESULT_DELIVERED')
        self.assertFalse(self.p.exists()); self.assertEqual(len(self.calls),1)
    def test_timeout_preserves_and_reaps(self):
        pid=self.root/'pid'; before=self.p.read_bytes(); start=time.monotonic()
        script=f'import os,time; open({str(pid)!r},"w").write(str(os.getpid())); time.sleep(10)'
        with self.fast(),self.assertRaisesRegex(ReceiptError,'RETRY_EXHAUSTED'):
            w.deliver(self.root,make_command=self.cmd(script))
        self.assertLess(time.monotonic()-start,4.5); self.assertEqual(self.p.read_bytes(),before)
        self.assertEqual(len(self.calls),3); self.assertEqual(len(set(self.calls)),1)
        with self.assertRaises(ProcessLookupError): os.kill(int(pid.read_text()),0)
    def test_total_deadline(self):
        before=self.p.read_bytes()
        with patch.multiple(w,TOTAL=.12,ATTEMPT=5,POLL=.01),self.assertRaisesRegex(ReceiptError,'DEADLINE_EXCEEDED'):
            w.deliver(self.root,make_command=self.cmd('import time; time.sleep(10)'))
        self.assertEqual(self.p.read_bytes(),before); self.assertEqual(len(self.calls),1)
    def test_stop_active_worker(self):
        before=self.p.read_bytes(); pid=self.root/'pid'
        def stop():
            end=time.monotonic()+2
            while not pid.exists() and time.monotonic()<end: time.sleep(.005)
            (self.root/'monitor.stop').touch()
        th=threading.Thread(target=stop); th.start()
        try:
            with patch.multiple(w,TOTAL=4,ATTEMPT=3,POLL=.01),self.assertRaisesRegex(ReceiptError,'STOP_REQUESTED'):
                w.deliver(self.root,make_command=self.cmd(f'import os,time; open({str(pid)!r},"w").write(str(os.getpid())); time.sleep(10)'))
        finally: th.join()
        self.assertEqual(self.p.read_bytes(),before); self.assertEqual(len(self.calls),1)
        with self.assertRaises(ProcessLookupError): os.kill(int(pid.read_text()),0)
    def test_stop_before_attempt(self):
        (self.root/'monitor.stop').touch()
        with self.assertRaisesRegex(ReceiptError,'STOP_REQUESTED'): w.deliver(self.root,make_command=self.cmd('raise SystemExit(0)'))
        self.assertTrue(self.p.exists()); self.assertEqual(self.calls,[])
    def test_stop_during_backoff(self):
        with patch.object(w,'attempt',side_effect=lambda *a: ((self.root/'monitor.stop').touch(),w.RETRY)[1]),self.assertRaisesRegex(ReceiptError,'STOP_REQUESTED'):
            w.deliver(self.root,make_command=self.cmd('raise SystemExit(10)'))
        self.assertTrue(self.p.exists()); self.assertEqual(len(self.calls),1)
    def test_bad_ack_and_reject(self):
        for rc,reason in [(11,'REJECTED'),(12,'ACK_INVALID'),(99,'REJECTED')]:
            with self.fast(),self.assertRaisesRegex(ReceiptError,reason): w.deliver(self.root,make_command=self.cmd(f'raise SystemExit({rc})'))
            self.assertTrue(self.p.exists())
    def test_claimed_never_sent_even_on_stop(self):
        self.j['state']='claimed_may_have_executed'; self.write(); (self.root/'monitor.stop').touch()
        with self.assertRaisesRegex(ReceiptError,'MANUAL_REVIEW'): w.deliver(self.root,make_command=self.cmd('raise SystemExit(0)'))
        self.assertEqual(self.calls,[])
    def test_changed_after_ack(self):
        script=f'from pathlib import Path; Path({str(self.p)!r}).write_text({json.dumps(dict(self.j,output="changed"))!r})'
        with self.fast(),self.assertRaisesRegex(ReceiptError,'CHANGED_AFTER_ACK'): w.deliver(self.root,make_command=self.cmd(script))
        self.assertTrue(self.p.exists())
    def test_worker_exact_payload_and_no_unlink(self):
        ident,_=record(self.p); calls=[]
        rc=w.receipt_only(self.root,w.digest(ident),lambda j,p: calls.append((j,p)) or {'ok':True})
        self.assertEqual(rc,w.ACK); self.assertEqual(calls,[(self.j['job_id'],{k:self.j[k] for k in ('lease_id','exit_code','output')})]); self.assertTrue(self.p.exists())
        self.assertEqual(w.receipt_only(self.root,'0'*64,lambda *a:self.fail('unexpected submit')),w.REJECT)
    def test_worker_transient_classification(self):
        ident,_=record(self.p)
        def err(e):
            def f(*a): raise e
            return f
        self.assertEqual(w.receipt_only(self.root,w.digest(ident),err(TimeoutError())),w.RETRY)
        self.assertEqual(w.receipt_only(self.root,w.digest(ident),err(ValueError())),w.REJECT)
        self.assertTrue(self.p.exists())
    def test_http_lost_ack_real_child(self):
        seen=[]; release=threading.Event(); guard=threading.Lock()
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*a): pass
            def do_POST(self):
                raw=self.rfile.read(int(self.headers['Content-Length']))
                with guard:
                    seen.append((self.path,raw)); first=len(seen)==1
                if first: release.wait(5); return  # accepted, but no reply
                self.send_response(200); self.send_header('Content-Length','11'); self.end_headers(); self.wfile.write(b'{"ok":true}')
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        port=server.server_address[1]
        def make(d):
            self.calls.append(d)
            script=f"""import json, sys, urllib.request as u
from pathlib import Path
from ha_receipt_watchdog import receipt_only
def submit(j,p):
    with u.urlopen(u.Request('http://127.0.0.1:{port}/result/'+j,data=json.dumps(p).encode()),timeout=5) as r: return json.load(r)
sys.exit(receipt_only(Path({str(self.root)!r}),{d!r},submit))
"""
            return [sys.executable,'-S','-c',script]
        try:
            with patch.multiple(w,TOTAL=4,ATTEMPT=.9,DELAYS=(.02,.04),POLL=.01):
                self.assertEqual(w.deliver(self.root,make_command=make),'RESULT_DELIVERED')
            self.assertEqual(len(seen),2); self.assertEqual(seen[0],seen[1]); self.assertFalse(self.p.exists())
            self.assertEqual(len(self.calls),2); self.assertEqual(len(set(self.calls)),1)
        finally:
            release.set(); server.shutdown(); server.server_close(); thread.join()

    def test_monitor_ready_no_tick(self):
        with self.fast(): self.assertEqual(m.cycle(self.root,lambda *a:self.fail('claim'),lambda r:w.deliver(r,make_command=self.cmd('raise SystemExit(0)'))),('RUNNING','HA_AGENT_RESULT_DELIVERED'))
    def test_monitor_stop_pending(self):
        (self.root/'monitor.stop').touch()
        self.assertEqual(m.cycle(self.root,lambda *a:self.fail('claim')),('STOPPED','RECEIPT_RETAINED')); self.assertTrue(self.p.exists())
    def test_monitor_ordinary_stop_cooperative(self):
        self.p.unlink()
        def ordinary(r):
            (r/'monitor.stop').touch(); self.write()
            return subprocess.CompletedProcess([],3,'HA_AGENT_STOPPED_FAIL_CLOSED:URLError','')
        self.assertEqual(m.cycle(self.root,ordinary),('STOPPED','RECEIPT_RETAINED')); self.assertTrue(self.p.exists())
    def test_monitor_unknown_failure(self):
        self.p.unlink()
        def ordinary(r): raise subprocess.TimeoutExpired('fixture',135)
        with self.assertRaisesRegex(ReceiptError,'TICK_FAILED'): m.cycle(self.root,ordinary)
    def test_budget_and_preflight(self):
        self.assertEqual(m.NOMINAL_CHILD_BUDGET,117); self.assertEqual(m.REMOTE_COMMAND_MAX,45); self.assertEqual(m.CHILD_TIMEOUT,135)
        self.p.unlink()
        self.assertEqual(m.cycle(self.root,lambda r:subprocess.CompletedProcess([],4,'HA_AGENT_PREFLIGHT_UNAVAILABLE:TimeoutError','')),('DEGRADED','PREFLIGHT_UNAVAILABLE:TimeoutError'))
    def test_child_contract(self):
        with patch.object(m.subprocess,'run') as f:
            m.child_tick(self.root); self.assertEqual(f.call_args.kwargs['timeout'],135)

if __name__=='__main__': unittest.main()
