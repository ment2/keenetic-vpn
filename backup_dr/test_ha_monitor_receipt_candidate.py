import contextlib, errno, fcntl, io, json, os, subprocess, sys, tempfile, types, unittest
from pathlib import Path
from unittest.mock import patch
from ha_monitor_receipt_candidate import cycle, run, receipt_submit, child_tick, URL, CHILD_TIMEOUT
from ha_receipt_retry import ReceiptError

class MonitorIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.root=Path(self.tmp.name)
        self.j={'state':'result_ready','job_id':'11111111-1111-4111-8111-111111111111','lease_id':'22222222-2222-4222-8222-222222222222','exit_code':0,'output':'SYNTHETIC'}
        self.calls=[]; self.ticks=0; self.delays=[]
    def write(self,state='result_ready'):
        self.j['state']=state; p=self.root/'pending.json'; p.write_text(json.dumps(self.j)); p.chmod(0o600)
    def submit(self,j,p): self.calls.append((j,p)); return {'ok':True}
    def tick(self,rc=0,marker='HA_AGENT_IDLE',pending=None):
        def f(root):
            self.ticks+=1
            if pending: self.write(pending)
            return subprocess.CompletedProcess([],rc,marker,'not_logged')
        return f
    def cycle(self,ordinary=None,submit=None):
        return cycle(self.root,ordinary or self.tick(),submit or self.submit,sleep=self.delays.append)
    def test_idle(self): self.assertEqual(self.cycle(),('RUNNING','HA_AGENT_IDLE')); self.assertEqual(self.ticks,1)
    def test_preflight_retry_preserved(self):
        for cls in ('HTTPError','URLError','TimeoutError'):
            self.assertEqual(self.cycle(self.tick(4,'HA_AGENT_PREFLIGHT_UNAVAILABLE:'+cls)),('DEGRADED','PREFLIGHT_UNAVAILABLE:'+cls))
        self.assertEqual(self.calls,[])
    def test_invalid_preflight_marker(self):
        with self.assertRaisesRegex(ReceiptError,'TICK_FAILED'): self.cycle(self.tick(4,'HA_AGENT_PREFLIGHT_UNAVAILABLE:untrusted'))
    def test_unknown_claim_no_journal(self):
        with self.assertRaisesRegex(ReceiptError,'TICK_FAILED_MANUAL_REVIEW:TimeoutError'): self.cycle(self.tick(3,'HA_AGENT_STOPPED_FAIL_CLOSED:TimeoutError'))
        self.assertEqual(self.calls,[])
    def test_ready_startup(self):
        self.write(); self.assertEqual(self.cycle(),('RUNNING','HA_AGENT_RESULT_DELIVERED')); self.assertEqual(self.ticks,0); self.assertEqual(len(self.calls),1)
        self.assertEqual(self.cycle(),('RUNNING','HA_AGENT_IDLE')); self.assertEqual(self.ticks,1)
    def test_failed_child_ready(self):
        self.assertEqual(self.cycle(self.tick(3,'HA_AGENT_STOPPED_FAIL_CLOSED:URLError','result_ready')),('RUNNING','HA_AGENT_RESULT_DELIVERED')); self.assertEqual(self.ticks,1); self.assertEqual(len(self.calls),1)
    def test_child_timeout_ready(self):
        def f(root): self.write(); raise subprocess.TimeoutExpired('fixture',80)
        self.assertEqual(self.cycle(f),('RUNNING','HA_AGENT_RESULT_DELIVERED')); self.assertEqual(len(self.calls),1)
    def test_child_timeout_no_journal(self):
        def f(root): raise subprocess.TimeoutExpired('fixture',80)
        with self.assertRaisesRegex(ReceiptError,'TICK_FAILED'): self.cycle(f)
    def test_claimed_blocks(self):
        self.write('claimed_may_have_executed')
        with self.assertRaisesRegex(ReceiptError,'MANUAL_REVIEW'): self.cycle()
        self.assertEqual(self.ticks,0); self.assertEqual(self.calls,[])
    def test_failed_child_claimed_blocks(self):
        with self.assertRaisesRegex(ReceiptError,'MANUAL_REVIEW'): self.cycle(self.tick(3,'HA_AGENT_STOPPED_FAIL_CLOSED:URLError','claimed_may_have_executed'))
        self.assertEqual(self.calls,[])
    def test_stop_before_delivery(self):
        self.write(); (self.root/'monitor.stop').touch(); self.assertEqual(self.cycle(),('STOPPED','STOP_REQUESTED')); self.assertEqual(self.calls,[]); self.assertEqual(self.ticks,0)
    def test_run_stop_after_delivery(self):
        self.write()
        def sleep(_): (self.root/'monitor.stop').touch()
        self.assertEqual(run(self.root,self.tick(),self.submit,sleep=sleep),0); self.assertEqual(self.ticks,0); self.assertEqual(len(self.calls),1); self.assertEqual(json.loads((self.root/'monitor-state.json').read_text())['status'],'STOPPED')
    def test_run_exhaustion(self):
        self.write()
        def fail(*a): raise OSError(errno.ENETUNREACH,'fixture')
        self.assertEqual(run(self.root,self.tick(),fail,sleep=self.delays.append),3); self.assertEqual(self.ticks,0); self.assertTrue((self.root/'pending.json').exists()); self.assertEqual(self.delays,[1,3]); self.assertEqual(json.loads((self.root/'monitor-state.json').read_text())['detail'],'RESULT_RETRY_EXHAUSTED')
    def test_monitor_lock_exclusion(self):
        fd=os.open(self.root/'monitor.lock',os.O_CREAT|os.O_RDWR,0o600)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(run(self.root,self.tick(),self.submit),2)
            self.assertEqual(self.ticks,0)
        finally: os.close(fd)
    def test_adapter_exact_route_preflight(self):
        calls=[]
        a=types.SimpleNamespace(preflight=lambda u:calls.append(('preflight',u)),read_token=lambda:'fixture-token',api=lambda *args: calls.append(args) or {'ok':True})
        with patch.dict(sys.modules,{'ha_bridge_tick':a}): self.assertEqual(receipt_submit(self.j['job_id'],{'exit_code':0}),{'ok':True})
        self.assertEqual(calls,[('preflight',URL),('POST',URL+'/v1/agent/result/'+self.j['job_id'],'fixture-token',{'exit_code':0})])
    def test_adapter_preflight_failure_no_post(self):
        def fail(u): raise TimeoutError()
        a=types.SimpleNamespace(preflight=fail,read_token=lambda:self.fail('token read'),api=lambda *a:self.fail('unexpected POST'))
        with patch.dict(sys.modules,{'ha_bridge_tick':a}), self.assertRaises(TimeoutError): receipt_submit(self.j['job_id'],{})
    def test_child_contract(self):
        with patch('ha_monitor_receipt_candidate.subprocess.run') as r:
            child_tick(self.root); r.assert_called_once_with([sys.executable,str(self.root/'ha_bridge_tick.py'),'--once','--url',URL],capture_output=True,text=True,timeout=CHILD_TIMEOUT)
