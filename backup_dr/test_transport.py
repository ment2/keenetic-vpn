import unittest,tempfile,threading,pathlib,sqlite3,tarfile,io,urllib.error
from transport import receiver,upload,encrypt_archive,keys,store
from crypto import open_sealed
from snapshot import archive
class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=pathlib.Path(self.tmp.name); self.key=bytes(range(32)); self.s=receiver(self.root,self.key,'127.0.0.1',('127.0.0.1',0)); self.t=threading.Thread(target=self.s.serve_forever); self.t.start(); self.url='http://127.0.0.1:%d/v1/backup'%self.s.server_port
    def tearDown(self): self.s.shutdown(); self.t.join(); self.s.server_close(); self.tmp.cleanup()
    def test_roundtrip_replay(self):
        b=encrypt_archive(self.key,b'example'); d=upload(self.url,self.key,b); self.assertEqual(upload(self.url,self.key,b),d); self.assertEqual(len(list(self.root.iterdir())),1); self.assertEqual(open_sealed(keys(self.key)[0],(self.root/(d+'.gcm')).read_bytes()),b'example')
    def test_tamper(self):
        b=encrypt_archive(self.key,b'example'); self.assertRaises(urllib.error.HTTPError,upload,self.url,self.key,b[:-1]+bytes([b[-1]^1])); self.assertEqual(list(self.root.iterdir()),[])
    def test_wrong_key(self):
        self.assertRaises(urllib.error.HTTPError,upload,self.url,bytes(32),encrypt_archive(bytes(32),b'bad')); self.assertEqual(list(self.root.iterdir()),[])
    def test_sqlite_restore(self):
        p=self.root/'live.db'; c=sqlite3.connect(p); c.execute('pragma journal_mode=wal'); c.execute('create table t(x)'); c.execute('insert into t values(42)'); c.commit()
        try:
            a=archive(self.root,[('live.db','sqlite')]); d=upload(self.url,self.key,encrypt_archive(self.key,a)); restored=open_sealed(keys(self.key)[0],(self.root/(d+'.gcm')).read_bytes());
            with tarfile.open(fileobj=io.BytesIO(restored)) as t: (self.root/'restored.db').write_bytes(t.extractfile('live.db').read())
            with sqlite3.connect(self.root/'restored.db') as r: self.assertEqual(r.execute('select x from t').fetchone(),(42,))
        finally: c.close()
    def test_traversal(self): self.assertRaises(ValueError,archive,self.root,[('../outside','file')])
