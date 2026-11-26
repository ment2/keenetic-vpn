"""Synthetic crash windows and group generation migration; no device access."""
import hashlib,json,os,pathlib,tempfile,threading,unittest
from unittest.mock import patch
import pending_envelope as env
import runtime,group_registry as registry,group_runtime as gr
from groups import config_id,group_key
from transport import encrypt_archive,keys,upload
from crypto import open_sealed
from snapshot import archive
from manifest import restore

class EnvelopeTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup)
        self.root=pathlib.Path(t.name); self.src=self.root/'src'; self.src.mkdir()
        (self.src/'a').write_bytes(b'old'); self.work=self.root/'work'; self.work.mkdir(mode=0o700)
        self.key=bytes(32); self.entries=[('a','file')]; self.config=config_id(self.entries)
        self.source=runtime.fingerprint(self.src,self.entries); self.blob=encrypt_archive(self.key,archive(self.src,self.entries)); self.path=self.work/'pending.envelope'; self.stage=self.work/'pending.envelope.tmp'; self.sent=[]
    def send(self,url,key,blob):
        self.sent.append(blob); return hashlib.sha256(blob).hexdigest()
    def tick(self): return runtime.tick(self.work,self.src,self.entries,self.key,'http://fixture',now=4000,send=self.send)
    def test_complete_stage_recovered_after_interrupted_rename(self):
        with patch('pending_envelope.os.replace',side_effect=OSError('synthetic interrupted rename')):
            with self.assertRaises(OSError): env.write(self.path,self.key,self.config,self.source,self.blob)
        self.assertTrue(self.stage.exists()); self.assertFalse(self.path.exists()); (self.src/'a').unlink()
        self.assertEqual(self.tick(),'accepted'); self.assertEqual(self.sent,[self.blob]); self.assertFalse(self.stage.exists()); self.assertFalse(self.path.exists())
    def test_directory_fsync_failure_recovers_committed_envelope(self):
        with patch('pending_envelope.sync_dir',side_effect=OSError('synthetic directory sync failure')):
            with self.assertRaises(OSError): env.write(self.path,self.key,self.config,self.source,self.blob)
        self.assertEqual(self.tick(),'accepted'); self.assertEqual(self.sent,[self.blob])
    def test_partial_stage_not_replaced(self):
        self.stage.write_bytes(b'partial'); self.stage.chmod(0o600)
        with self.assertRaises(ValueError): self.tick()
        self.assertEqual(self.stage.read_bytes(),b'partial'); self.assertFalse(self.path.exists()); self.assertEqual(self.sent,[])
    def test_authenticated_metadata_tamper(self):
        env.write(self.path,self.key,self.config,self.source,self.blob); raw=self.path.read_bytes(); self.path.write_bytes(raw.replace(self.source.encode(),b'f'*64,1))
        with self.assertRaises(ValueError): self.tick()
        self.assertEqual(self.sent,[]); self.assertTrue(self.path.exists())
    def test_wrong_config_key_rejected(self):
        env.write(self.path,self.key,self.config,self.source,self.blob)
        for k,c in ((b'1'*32,self.config),(self.key,'f'*64)):
            with self.assertRaises(ValueError): env.read(self.path,k,c)
        self.assertEqual(self.sent,[])
    def test_two_envelope_names_fail_closed(self):
        env.write(self.path,self.key,self.config,self.source,self.blob); self.stage.write_bytes(self.path.read_bytes()); self.stage.chmod(0o600)
        with self.assertRaisesRegex(ValueError,'conflicting'): self.tick()
        self.assertTrue(self.path.exists() and self.stage.exists()); self.assertEqual(self.sent,[])
    def test_legacy_pending_remains_deliverable(self):
        p=self.work/'pending.gcm'; p.write_bytes(self.blob); p.chmod(0o600)
        runtime.atomic(self.work/'state.json',json.dumps({'pending':{'source':self.source,'sha256':hashlib.sha256(self.blob).hexdigest()}}).encode()); (self.src/'a').unlink()
        self.assertEqual(self.tick(),'accepted'); self.assertEqual(self.sent,[self.blob]); self.assertFalse(p.exists())
    def test_legacy_and_envelope_conflict(self):
        env.write(self.path,self.key,self.config,self.source,self.blob); p=self.work/'pending.gcm'; p.write_bytes(self.blob); p.chmod(0o600)
        with self.assertRaisesRegex(ValueError,'conflicting'): self.tick()
        self.assertTrue(p.exists() and self.path.exists()); self.assertEqual(self.sent,[])
    def test_envelope_and_state_mismatch_retained(self):
        env.write(self.path,self.key,self.config,self.source,self.blob); runtime.atomic(self.work/'state.json',json.dumps({'pending':{'source':self.source,'sha256':'a'*64,'format':'envelope-v1'}}).encode())
        with self.assertRaisesRegex(ValueError,'metadata mismatch'): self.tick()
        self.assertTrue(self.path.exists()); self.assertEqual(self.sent,[])

class GenerationTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup); self.root=pathlib.Path(t.name)
        self.src=self.root/'src'; self.src.mkdir(); (self.src/'a').write_bytes(b'old'); (self.src/'b').write_bytes(b'new')
        self.sender=self.root/'sender'; self.sender.mkdir(mode=0o700); self.receiver=self.root/'receiver'; self.receiver.mkdir(mode=0o700); self.key=bytes(32)
        self.old={'alpha':[['a','file']]}; self.new={'alpha':[['b','file']]}; self.old_id=config_id(self.old['alpha']); self.new_id=config_id(self.new['alpha'])
        registry.ensure(self.sender,self.key,'sender',self.old); registry.ensure(self.receiver,self.key,'receiver',self.old)
    def test_unapproved_change_fails_both_roles(self):
        self.assertEqual(gr.run_tick(self.sender,self.src,self.new,self.key,'http://fixture',now=1),{'alpha':'retry_required'})
        with self.assertRaisesRegex(ValueError,'approval'): gr.make_receiver(self.receiver,self.key,self.new,{'alpha':100000},'127.0.0.1',('127.0.0.1',0),reserve=0)
        with self.assertRaisesRegex(ValueError,'explicit'): registry.approve_change(self.sender,self.key,'sender',self.old,self.new)
        self.assertEqual(registry.read(self.sender,self.key,'sender')['active'],{'alpha':self.old_id})
    def test_pending_generation_blocks_change(self):
        self.assertEqual(gr.run_tick(self.sender,self.src,self.old,self.key,'http://fixture',now=1),{'alpha':'idle'})
        with patch('runtime.upload',side_effect=OSError('network')): # tick captures its default; use explicit send
            p=self.sender/'alpha'/self.old_id
            with self.assertRaises(OSError): runtime.tick(p,self.src,[('a','file')],group_key(self.key,'alpha'),'http://fixture',now=3601,send=lambda *_: (_ for _ in ()).throw(OSError('lost receipt')))
        with self.assertRaisesRegex(ValueError,'drained'): registry.approve_change(self.sender,self.key,'sender',self.old,self.new,coordinated=True)
        self.assertTrue((p/'pending.envelope').exists())
    def test_busy_service_blocks_change(self):
        with registry.exclusive(self.sender/'service.lock'):
            with self.assertRaises(BlockingIOError): registry.approve_change(self.sender,self.key,'sender',self.old,self.new,coordinated=True)
    def test_registry_tamper_blocks_sender(self):
        p=self.sender/registry.NAME; raw=p.read_bytes(); p.write_bytes(raw.replace(self.old_id.encode(),self.new_id.encode(),1))
        self.assertEqual(gr.run_tick(self.sender,self.src,self.new,self.key,'http://fixture',now=1),{'alpha':'retry_required'})
    def test_historical_archive_retained_and_restorable_real_http(self):
        def receiver(config):
            s=gr.make_receiver(self.receiver,self.key,config,{'alpha':100000},'127.0.0.1',('127.0.0.1',0),reserve=0)
            t=threading.Thread(target=s.serve_forever); t.start(); return s,t
        def run(config,now):
            s,t=receiver(config)
            try:
                origin='http://127.0.0.1:%s'%s.server_port
                self.assertEqual(gr.run_tick(self.sender,self.src,config,self.key,origin,now=now),{'alpha':'idle'})
                self.assertEqual(gr.run_tick(self.sender,self.src,config,self.key,origin,now=now+3600),{'alpha':'accepted'})
            finally: s.shutdown(); t.join(); s.server_close()
        run(self.old,1); old=next((self.receiver/'alpha').glob('*.gcm')); oldbytes=old.read_bytes(); os.utime(old,(1,1))
        for role,root in [('sender',self.sender),('receiver',self.receiver)]: registry.approve_change(root,self.key,role,self.old,self.new,coordinated=True)
        run(self.new,5000)
        key=group_key(self.key,'alpha')
        for _ in range(3):
            from transport import store
            store(self.receiver/'alpha',encrypt_archive(key,archive(self.src,[('b','file')])))
        for p in (self.receiver/'alpha').glob('*.gcm'): os.utime(p,(1,1))
        gr.prune_groups(self.receiver,self.new,self.key,now=40*86400)
        self.assertEqual(old.read_bytes(),oldbytes)
        out=restore(open_sealed(keys(key)[0],oldbytes),self.root); self.assertEqual((out/'a').read_bytes(),b'old'); self.assertFalse((out/'b').exists())
        for role,root in [('sender',self.sender),('receiver',self.receiver)]: registry.approve_change(root,self.key,role,self.new,self.old,coordinated=True)
        self.assertEqual(gr.prune_groups(self.receiver,self.old,self.key,now=80*86400),{'alpha':[]}); self.assertTrue(old.exists())
    def test_unregistered_legacy_generation_rejected(self):
        root=self.root/'legacy'; root.mkdir(mode=0o700); g=root/'alpha';g.mkdir(mode=0o700); (g/self.old_id).mkdir(mode=0o700)
        with self.assertRaisesRegex(ValueError,'unregistered'): registry.ensure(root,self.key,'sender',self.new)
        self.assertFalse((root/registry.NAME).exists())

if __name__=='__main__': unittest.main()
