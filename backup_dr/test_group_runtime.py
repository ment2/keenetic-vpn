import pathlib,tempfile,threading,unittest,urllib.error,sqlite3
from groups import group_key
from group_runtime import make_receiver,run_tick,group_status
from transport import upload,encrypt_archive,keys
from snapshot import archive
from crypto import open_sealed
from manifest import restore

class GroupRuntime(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=pathlib.Path(self.tmp.name)
        self.source=self.root/'source'; self.source.mkdir(); (self.source/'a').write_bytes(b'alpha'); (self.source/'b').write_bytes(b'beta')
        self.db=sqlite3.connect(self.source/'test.db'); self.db.execute('pragma journal_mode=wal'); self.db.execute('create table t(x)'); self.db.execute('insert into t values(42)'); self.db.commit()
        self.config={'alpha':[['a','file']],'beta':[['b','file'],['test.db','sqlite']]}; self.master=bytes(range(32)); self.dest=self.root/'dest'; self.s=make_receiver(self.dest,self.master,self.config,{'alpha':100000,'beta':100000},'127.0.0.1',('127.0.0.1',0),reserve=0)
        self.thread=threading.Thread(target=self.s.serve_forever); self.thread.start(); self.origin='http://127.0.0.1:%s'%self.s.server_port
    def tearDown(self):
        self.s.shutdown(); self.thread.join(); self.s.server_close(); self.db.close(); self.tmp.cleanup()
    def test_schedule_restore(self):
        args=(self.root/'state',self.source,self.config,self.master,self.origin)
        self.assertEqual(run_tick(*args,now=100),{'alpha':'idle','beta':'idle'})
        self.assertEqual(run_tick(*args,now=3700),{'alpha':'accepted','beta':'accepted'})
        self.assertEqual(run_tick(*args,now=3701),{'alpha':'idle','beta':'idle'})
        f=next((self.dest/'beta').glob('*.gcm')); out=restore(open_sealed(keys(group_key(self.master,'beta'))[0],f.read_bytes()),self.root)
        c=sqlite3.connect(out/'test.db')
        try: self.assertEqual(c.execute('select x from t').fetchall(),[(42,)])
        finally: c.close()
        self.assertEqual(group_status(self.dest,self.config,reserve=0)['archive_count'],2)
    def test_wrong_group(self):
        data=archive(self.source,[('a','file')]); key=group_key(self.master,'beta')
        with self.assertRaises(urllib.error.HTTPError): upload(self.origin+'/v1/backup/beta',key,encrypt_archive(key,data))
        self.assertEqual(list((self.dest/'beta').iterdir()),[])
    def test_quota_plan(self):
        with self.assertRaises(ValueError): make_receiver(self.root/'other',self.master,self.config,{'alpha':10,'beta':10},'127.0.0.1',('127.0.0.1',0),total_budget=19,reserve=0)
