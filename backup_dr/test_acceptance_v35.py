"""Synthetic end-to-end acceptance: HTTP durable commit before lost receipt, restart, restore."""
import contextlib,hashlib,pathlib,sqlite3,tempfile,threading,unittest
from group_runtime import make_receiver
from groups import group_key
from runtime import tick
from pending_envelope import read
from groups import config_id
from transport import upload,keys
from crypto import open_sealed
from manifest import restore

class Acceptance(unittest.TestCase):
    def test_lost_ack_restart_exact_ciphertext_sqlite_restore(self):
        with tempfile.TemporaryDirectory() as d:
            r=pathlib.Path(d); source=r/'source'; source.mkdir(); work=r/'work'; dest=r/'dest'; master=bytes(range(32)); cfg={'state':[['fixture.txt','file'],['fixture.db','sqlite']]}; q={'state':1000000}; key=group_key(master,'state')
            (source/'fixture.txt').write_bytes(b'fixture-v35'); db=sqlite3.connect(source/'fixture.db'); db.execute('pragma journal_mode=wal'); db.execute('create table t(x)'); db.execute('insert into t values(42)'); db.commit()
            def start():
                s=make_receiver(dest,master,cfg,q,'127.0.0.1',('127.0.0.1',0),reserve=0); t=threading.Thread(target=s.serve_forever); t.start(); return s,t,f'http://127.0.0.1:{s.server_port}/v1/backup/state'
            def stop(s,t): s.shutdown(); t.join(); s.server_close()
            s,t,url=start(); calls=[]
            def lose(url,key,blob):
                calls.append(blob); upload(url,key,blob); raise OSError('synthetic receipt loss after durable server commit')
            try:
                self.assertEqual(tick(work,source,cfg['state'],key,url,now=100),'idle')
                with self.assertRaises(OSError): tick(work,source,cfg['state'],key,url,now=3700,send=lose)
                self.assertEqual(read(work/'pending.envelope',key,config_id(cfg['state']))[1],calls[0]); self.assertEqual(len(list((dest/'state').glob('*.gcm'))),1)
            finally: stop(s,t)
            s,t,url=start()
            def retry(url,key,blob): calls.append(blob); return upload(url,key,blob)
            try:
                self.assertEqual(tick(work,source,cfg['state'],key,url,now=3701,send=retry),'accepted'); self.assertEqual(calls[0],calls[1]); self.assertFalse((work/'pending.envelope').exists()); self.assertEqual(tick(work,source,cfg['state'],key,url,now=9999),'idle')
                files=list((dest/'state').glob('*.gcm')); self.assertEqual(len(files),1); b=files[0].read_bytes(); self.assertEqual(hashlib.sha256(b).hexdigest(),files[0].stem)
                out=restore(open_sealed(keys(key)[0],b),r); self.assertEqual((out/'fixture.txt').read_bytes(),b'fixture-v35')
                with contextlib.closing(sqlite3.connect(out/'fixture.db')) as check: self.assertEqual(check.execute('pragma quick_check').fetchone(),('ok',)); self.assertEqual(check.execute('select x from t').fetchall(),[(42,)])
                self.assertEqual(db.execute('select x from t').fetchall(),[(42,)])
            finally: stop(s,t); db.close()
