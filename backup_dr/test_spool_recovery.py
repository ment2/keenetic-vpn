"""Synthetic sender recovery regression; no real source files or keys."""
import hashlib,json,pathlib,tempfile,unittest,threading
from unittest.mock import patch
import runtime,group_runtime
from groups import config_id,group_key
from pending_envelope import read
from resource_guard import SOURCE_MAX
from transport import upload

class SpoolRecovery(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=pathlib.Path(self.tmp.name); self.src=self.root/'source'; self.src.mkdir()
        self.f=self.src/'a'; self.f.write_bytes(b'v1'); self.work=self.root/'work'; self.calls=[]
        self.args=(self.work,self.src,[('a','file')],bytes(32),'http://fixture')
    def ok(self,url,key,blob):
        self.calls.append(blob); return hashlib.sha256(blob).hexdigest()
    def fail(self,url,key,blob):
        self.calls.append(blob); raise OSError('synthetic lost receipt')
    def pending(self):
        self.assertEqual(runtime.tick(*self.args,now=100,send=self.ok),'idle')
        with self.assertRaises(OSError): runtime.tick(*self.args,now=3700,send=self.fail)
        return read(self.work/'pending.envelope',self.args[3],config_id(self.args[2]))[1]
    def test_missing_source_retry_does_not_preflight(self):
        old=self.pending(); self.f.unlink()
        def forbidden(): raise AssertionError('source preflight must not run')
        self.assertEqual(runtime.tick(*self.args,now=3701,send=self.ok,source_ready=forbidden),'accepted')
        self.assertEqual(self.calls,[old,old]); self.assertFalse((self.work/'pending.envelope').exists())
    def test_oversize_source_retry_then_gate_fresh(self):
        old=self.pending(); self.f.write_bytes(b'x'*(SOURCE_MAX+1))
        self.assertEqual(runtime.tick(*self.args,now=3701,send=self.ok,source_ready=lambda:False),'accepted')
        self.assertEqual(self.calls,[old,old])
        self.assertEqual(runtime.tick(*self.args,now=3702,send=self.ok,source_ready=lambda:False),'preflight_failed')
        self.assertEqual(len(self.calls),2)
    def test_missing_pending_spool_never_resnapshot(self):
        self.pending(); (self.work/'pending.envelope').unlink()
        before=(self.work/'state.json').read_bytes()
        with patch('runtime.archive',side_effect=AssertionError('unexpected archive')):
            with self.assertRaises(OSError): runtime.tick(*self.args,now=4000,send=self.ok)
        self.assertEqual((self.work/'state.json').read_bytes(),before); self.assertEqual(len(self.calls),1)
    def test_corrupt_pending_spool_retained(self):
        self.pending(); p=self.work/'pending.envelope'; p.write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError,'envelope'): runtime.tick(*self.args,now=4000,send=self.ok)
        self.assertEqual(p.read_bytes(),b'corrupt'); self.assertEqual(len(self.calls),1)
    def test_crash_after_ack_state_no_duplicate(self):
        old=self.pending(); p=self.work/'pending.envelope'
        with patch('runtime.remove_spool',side_effect=OSError('synthetic crash after state commit')):
            with self.assertRaises(OSError): runtime.tick(*self.args,now=3701,send=self.ok)
        self.assertEqual(read(p,self.args[3],config_id(self.args[2]))[1],old); self.assertEqual(json.loads((self.work/'state.json').read_text())['accepted_spool'],hashlib.sha256(old).hexdigest())
        self.assertEqual(runtime.tick(*self.args,now=3702,send=self.ok),'idle'); self.assertFalse(p.exists()); self.assertEqual(self.calls,[old,old])
    def test_envelope_recovers_after_crash_before_state(self):
        self.assertEqual(runtime.tick(*self.args,now=100,send=self.ok),'idle'); real=runtime.atomic
        def fail_state(path,data):
            if path.name=='state.json': raise OSError('synthetic crash before pending commit')
            return real(path,data)
        with patch('runtime.atomic',side_effect=fail_state):
            with self.assertRaises(OSError): runtime.tick(*self.args,now=3700,send=self.ok)
        p=self.work/'pending.envelope'; old=read(p,self.args[3],config_id(self.args[2]))[1]; self.f.unlink()
        self.assertEqual(runtime.tick(*self.args,now=3701,send=self.ok),'accepted')
        self.assertEqual(self.calls,[old]); self.assertFalse(p.exists())
    def test_receipt_mismatch_preserves_pending(self):
        old=self.pending(); before=(self.work/'state.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'receipt mismatch'): runtime.tick(*self.args,now=3701,send=lambda *_:'0'*64)
        self.assertEqual(read(self.work/'pending.envelope',self.args[3],config_id(self.args[2]))[1],old); self.assertEqual((self.work/'state.json').read_bytes(),before)
    def test_symlink_pending_rejected(self):
        old=self.pending(); p=self.work/'pending.envelope'; raw=p.read_bytes(); p.unlink(); target=self.root/'other'; target.write_bytes(raw); target.chmod(0o600); p.symlink_to(target)
        with self.assertRaises(OSError): runtime.tick(*self.args,now=3701,send=self.ok)
        self.assertTrue(p.is_symlink()); self.assertEqual(target.read_bytes(),raw); self.assertEqual(len(self.calls),1)
    def test_group_lost_ack_missing_source_real_http(self):
        self.f.write_bytes(b'alpha'); (self.src/'b').write_bytes(b'beta'); cfg={'alpha':[['a','file']],'beta':[['b','file']]}; dest=self.root/'dest'; master=bytes(32)
        s=group_runtime.make_receiver(dest,master,cfg,{'alpha':100000,'beta':100000},'127.0.0.1',('127.0.0.1',0),reserve=0)
        t=threading.Thread(target=s.serve_forever); t.start()
        try:
            args=(self.root/'groups',self.src,cfg,master,f'http://127.0.0.1:{s.server_port}')
            self.assertEqual(group_runtime.run_tick(*args,now=100),{'alpha':'idle','beta':'idle'})
            def lose(url,key,blob):
                ack=upload(url,key,blob)
                if url.endswith('/alpha'): self.calls.append(blob); raise OSError('lost receipt')
                return ack
            with patch('group_runtime.tick',side_effect=lambda *a,**kw: runtime.tick(*a,send=lose,**kw)):
                self.assertEqual(group_runtime.run_tick(*args,now=3700),{'alpha':'retry_required','beta':'accepted'})
            p=self.root/'groups'/'alpha'/config_id([('a','file')])/'pending.envelope'; self.assertTrue(p.is_file()); old=read(p,group_key(master,'alpha'),config_id([('a','file')]))[1]; self.f.unlink(); (self.src/'b').write_bytes(b'changed')
            def retry(url,key,blob): self.calls.append(blob); return upload(url,key,blob)
            with patch('group_runtime.tick',side_effect=lambda *a,**kw: runtime.tick(*a,send=retry,**kw)):
                self.assertEqual(group_runtime.run_tick(*args,now=3701),{'alpha':'accepted','beta':'idle'})
            self.assertEqual(self.calls,[old,old]); self.assertEqual(len(list((dest/'alpha').glob('*.gcm'))),1); self.assertFalse(p.exists())
            self.assertEqual(group_runtime.run_tick(*args,now=3702),{'alpha':'preflight_failed','beta':'idle'})
        finally: s.shutdown(); t.join(); s.server_close()
