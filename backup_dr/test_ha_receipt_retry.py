import errno,json,os,ssl,tempfile,unittest,urllib.error,fcntl
from pathlib import Path
from ha_receipt_retry import deliver_pending,ReceiptError

class ReceiptRetry(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name); self.p=self.root/'pending.json'
        self.j={'state':'result_ready','job_id':'11111111-1111-4111-8111-111111111111','lease_id':'22222222-2222-4222-8222-222222222222','exit_code':0,'output':'SYNTHETIC_RESULT'}
        self.write(); self.calls=[]; self.delays=[]
    def write(self):
        self.p.write_text(json.dumps(self.j)); self.p.chmod(0o600)
    def run_delivery(self,fn):
        def submit(job,payload):
            self.calls.append((job,dict(payload))); return fn()
        return deliver_pending(self.root,submit,sleep=self.delays.append)
    def test_loss_then_ack(self):
        def fn():
            if len(self.calls)==1: raise urllib.error.URLError(TimeoutError())
            return {'ok':True,'already_received':True}
        self.assertEqual(self.run_delivery(fn),'RESULT_DELIVERED'); self.assertEqual(self.calls[0],self.calls[1]); self.assertEqual(self.delays,[1]); self.assertFalse(self.p.exists())
    def test_exhaustion_preserves_restart(self):
        before=self.p.read_bytes()
        def fn(): raise ConnectionResetError(errno.ECONNRESET,'synthetic')
        with self.assertRaisesRegex(ReceiptError,'EXHAUSTED'): self.run_delivery(fn)
        self.assertEqual(len(self.calls),3); self.assertEqual(self.delays,[1,3]); self.assertEqual(before,self.p.read_bytes()); self.assertEqual(self.run_delivery(lambda:{'ok':True}),'RESULT_DELIVERED'); self.assertTrue(all(c==self.calls[0] for c in self.calls))
    def test_no_pending(self):
        self.p.unlink(); self.assertEqual(self.run_delivery(lambda:self.fail('unexpected submit')),'ABSENT')
    def test_claimed_never_sent(self):
        self.j['state']='claimed_may_have_executed'; self.write()
        with self.assertRaisesRegex(ReceiptError,'MANUAL_REVIEW'): self.run_delivery(lambda:self.fail('unexpected submit'))
        self.assertEqual(self.calls,[])
    def test_http_permanent(self):
        for code in (400,401,403,404,409,429):
            with self.subTest(code=code):
                self.calls.clear(); self.delays.clear()
                def fn(): raise urllib.error.HTTPError('https://example.invalid',code,'synthetic',None,None)
                with self.assertRaisesRegex(ReceiptError,'REJECTED'): self.run_delivery(fn)
                self.assertEqual(len(self.calls),1); self.assertTrue(self.p.exists()); self.assertFalse(self.delays)
    def test_http_temporary(self):
        def fn():
            if len(self.calls)==1: raise urllib.error.HTTPError('https://example.invalid',503,'synthetic',None,None)
            return {'ok':True}
        self.assertEqual(self.run_delivery(fn),'RESULT_DELIVERED'); self.assertEqual(self.delays,[1])
    def test_bad_ack(self):
        for ack in ({'ok':1},{'ok':False},None):
            with self.assertRaisesRegex(ReceiptError,'ACK_INVALID'): self.run_delivery(lambda:ack)
            self.assertTrue(self.p.exists())
    def test_tls_failure(self):
        def fn(): raise urllib.error.URLError(ssl.SSLCertVerificationError('synthetic'))
        with self.assertRaisesRegex(ReceiptError,'REJECTED'): self.run_delivery(fn)
        self.assertEqual(len(self.calls),1)
    def test_malformed(self):
        self.p.write_text('{"state":"result_ready","state":"result_ready"}')
        with self.assertRaises(ReceiptError): self.run_delivery(lambda:self.fail('unexpected submit'))
        self.assertFalse(self.calls)
    def test_symlink(self):
        self.p.rename(self.root/'other'); self.p.symlink_to(self.root/'other')
        with self.assertRaises(ReceiptError): self.run_delivery(lambda:self.fail('unexpected submit'))
        self.assertTrue(self.p.is_symlink())
    def test_changed_after_ack(self):
        def fn(): self.j['output']='changed'; self.write(); return {'ok':True}
        with self.assertRaisesRegex(ReceiptError,'CHANGED_AFTER_ACK'): self.run_delivery(fn)
        self.assertTrue(self.p.exists())
    def test_lock(self):
        with open(self.root/'agent.lock','w') as f:
            os.chmod(f.name,0o600); fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaisesRegex(ReceiptError,'AGENT_BUSY'): self.run_delivery(lambda:self.fail('unexpected submit'))
    def test_invalid_identity_and_output(self):
        self.j['lease_id']='bad'; self.write()
        with self.assertRaisesRegex(ReceiptError,'INVALID_JOURNAL_IDENTITY'): self.run_delivery(lambda:self.fail('unexpected submit'))
        self.j['lease_id']='22222222-2222-4222-8222-222222222222'; self.j['output']='x'*16001; self.write()
        with self.assertRaisesRegex(ReceiptError,'INVALID_RESULT'): self.run_delivery(lambda:self.fail('unexpected submit'))
        self.assertFalse(self.calls)

class MonitorCycle(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.root=Path(self.tmp.name)
        self.j={'state':'result_ready','job_id':'11111111-1111-4111-8111-111111111111','lease_id':'22222222-2222-4222-8222-222222222222','exit_code':0,'output':'SYNTHETIC_RESULT'}
        self.calls=[]; self.ticks=0
    def write(self):
        p=self.root/'pending.json'; p.write_text(json.dumps(self.j)); p.chmod(0o600)
    def submit(self,job,payload):
        self.calls.append((job,payload)); return {'ok':True}
    def cycle(self,fn):
        from ha_receipt_retry import monitor_cycle
        def tick(): self.ticks+=1; return fn()
        return monitor_cycle(self.root,self.submit,tick,sleep=lambda _:None)
    def test_startup_ready_no_claim(self):
        self.write(); self.assertEqual(self.cycle(lambda:True),'RESULT_DELIVERED'); self.assertEqual(self.ticks,0)
        self.assertEqual(self.cycle(lambda:True),'TICK_ACKNOWLEDGED'); self.assertEqual(self.ticks,1)
    def test_failed_tick_result_ready_no_reexecute(self):
        def fn(): self.write(); return False
        self.assertEqual(self.cycle(fn),'RESULT_DELIVERED'); self.assertEqual(self.ticks,1); self.assertEqual(len(self.calls),1)
    def test_failed_claim_without_journal(self):
        with self.assertRaisesRegex(ReceiptError,'TICK_FAILED_MANUAL_REVIEW'): self.cycle(lambda:False)
        self.assertEqual(self.ticks,1); self.assertEqual(self.calls,[])
    def test_failed_tick_claimed_journal(self):
        def fn(): self.j['state']='claimed_may_have_executed'; self.write(); return False
        with self.assertRaisesRegex(ReceiptError,'MANUAL_REVIEW'): self.cycle(fn)
        self.assertEqual(self.ticks,1); self.assertEqual(self.calls,[])

class LoopbackReceipt(unittest.TestCase):
    def test_committed_result_lost_response_then_same_receipt(self):
        import http.server,threading,socket,urllib.request
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); p=root/'pending.json'
            j={'state':'result_ready','job_id':'11111111-1111-4111-8111-111111111111','lease_id':'22222222-2222-4222-8222-222222222222','exit_code':0,'output':'SYNTHETIC_RESULT'}
            p.write_text(json.dumps(j)); p.chmod(0o600); stored=[]; received=[]
            class Handler(http.server.BaseHTTPRequestHandler):
                def log_message(self,*a): pass
                def do_POST(self):
                    body=self.rfile.read(int(self.headers['Content-Length'])); received.append((self.path,body))
                    if not stored:
                        stored.append((self.path,body)); self.connection.shutdown(socket.SHUT_RDWR); self.close_connection=True; return
                    if stored[0] != (self.path,body): self.send_error(409); return
                    b=b'{"ok":true,"already_received":true}'; self.send_response(200); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
            server=http.server.HTTPServer(('127.0.0.1',0),Handler); thread=threading.Thread(target=server.serve_forever); thread.start()
            opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
            def submit(job,payload):
                req=urllib.request.Request('http://127.0.0.1:'+str(server.server_port)+'/result/'+job,data=json.dumps(payload).encode(),method='POST')
                with opener.open(req,timeout=2) as res: return json.load(res)
            try:
                self.assertEqual(deliver_pending(root,submit,sleep=lambda _:None),'RESULT_DELIVERED')
                self.assertEqual(len(received),2); self.assertEqual(received[0],received[1]); self.assertEqual(len(stored),1); self.assertFalse(p.exists())
            finally: server.shutdown(); thread.join(); server.server_close()
