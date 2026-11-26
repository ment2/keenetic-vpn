import pathlib,tempfile,threading,unittest,urllib.error,json
from sender_monitor import Inbox,send_report,status_key,report,STALE,PATH
from group_runtime import make_receiver,run_tick
from transport import encrypt_archive,upload
from service_v35 import run_receiver

class SenderMonitor(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.r=pathlib.Path(self.tmp.name)
        self.key=bytes(range(32)); self.config={'alpha':[['a','file']]}; self.now=2000
        self.private=self.r/'private'; self.private.mkdir(mode=0o700)
        self.inbox=Inbox(self.private/'sender.gcm',self.key,self.config,clock=lambda:self.now)
        self.dest=self.r/'dest'; self.s=make_receiver(self.dest,self.key,self.config,{'alpha':100000},'127.0.0.1',('127.0.0.1',0),reserve=0,status_inbox=self.inbox)
        self.t=threading.Thread(target=self.s.serve_forever); self.t.start(); self.url=f'http://127.0.0.1:{self.s.server_port}'
    def tearDown(self):
        self.s.shutdown(); self.t.join(); self.s.server_close(); self.tmp.cleanup()
    def send(self,result='idle',now=None): return send_report(self.url,self.key,{'alpha':result},self.now if now is None else now)
    def test_missing_healthy_stale(self):
        self.assertEqual(self.inbox.summary()['status'],'missing'); self.send(); self.assertEqual(self.inbox.summary()['status'],'ok'); self.now+=STALE+1; self.assertEqual(self.inbox.summary()['status'],'stale')
    def test_replay_survives_restart(self):
        self.send(); new=Inbox(self.private/'sender.gcm',self.key,self.config,clock=lambda:self.now)
        b=encrypt_archive(status_key(self.key),json.dumps(report({'alpha':'retry_required'},self.now)).encode())
        with self.assertRaises(ValueError): new.accept(b)
        self.assertEqual(new.summary()['status'],'ok')
    def test_bad_key_and_clock(self):
        for k,t in [(b'x'*32,self.now),(self.key,self.now-STALE-1),(self.key,self.now+61)]:
            with self.assertRaises(urllib.error.HTTPError): send_report(self.url,k,{'alpha':'idle'},t)
        self.assertEqual(self.inbox.summary()['status'],'missing')
    def test_group_and_schema(self):
        for rows in ({'other':'idle'},{'alpha':'unknown'},{'alpha':{'path':'private'}}):
            with self.assertRaises(urllib.error.HTTPError): send_report(self.url,self.key,rows,self.now)
        self.assertEqual(self.inbox.summary()['status'],'missing')
    def test_end_to_end_and_failure(self):
        src=self.r/'src'; src.mkdir(); (src/'a').write_bytes(b'fixture')
        args=(self.r/'work',src,self.config,self.key,self.url)
        self.assertEqual(run_tick(*args,now=100),{'alpha':'idle'})
        results=run_tick(*args,now=3700); self.assertEqual(results,{'alpha':'accepted'}); send_report(self.url,self.key,results,self.now)
        self.assertEqual(self.inbox.summary()['groups'],results); self.assertEqual(len(list((self.dest/'alpha').glob('*.gcm'))),1)
        self.now+=1; (src/'a').unlink(); results=run_tick(*args,now=3701); send_report(self.url,self.key,results,self.now); self.assertEqual(self.inbox.summary()['status'],'retry_required')
    def test_state_outside_archive_and_private(self):
        self.send(); self.assertEqual((self.private/'sender.gcm').stat().st_mode&0o777,0o600); self.assertEqual(list((self.dest/'alpha').iterdir()),[])
        self.assertNotIn(b'heartbeat',(self.private/'sender.gcm').read_bytes())
