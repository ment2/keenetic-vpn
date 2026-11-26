import io, pathlib, tempfile, tarfile, unittest, threading, urllib.error
from snapshot import archive
from manifest import verify, restore
from transport import receiver, encrypt_archive, upload, store
from quota import QuotaExceeded
class ManifestQuota(unittest.TestCase):
    def test_isolated_restore(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d); (p/'a').write_bytes(b'abc'); b=archive(p,[('a','file')]); self.assertEqual(verify(b)['a'][1],b'abc'); self.assertEqual((restore(b,p)/'a').read_bytes(),b'abc')
    def test_missing_manifest(self):
        out=io.BytesIO()
        with tarfile.open(fileobj=out,mode='w:gz') as t:
            i=tarfile.TarInfo('a'); i.size=1; t.addfile(i,io.BytesIO(b'x'))
        self.assertRaises(ValueError,verify,out.getvalue())
    def test_manifest_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d); (p/'a').write_bytes(b'abc'); data=archive(p,[('a','file')]); out=io.BytesIO()
            with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as src, tarfile.open(fileobj=out,mode='w:gz') as dst:
                for i in src: dst.addfile(i,io.BytesIO(b'xyz' if i.name=='a' else src.extractfile(i).read()))
            self.assertRaises(ValueError,verify,out.getvalue())
    def test_quota_idempotence(self):
        with tempfile.TemporaryDirectory() as d:
            a=b'abc'; digest=store(d,a,budget=3); self.assertEqual(store(d,a,budget=3),digest); self.assertRaises(QuotaExceeded,store,d,b'x',3)
    def test_http_strict(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d); (p/'a').write_bytes(b'x'); key=bytes(32); s=receiver(p,key,'127.0.0.1',('127.0.0.1',0),reserve=0); t=threading.Thread(target=s.serve_forever); t.start(); url='http://127.0.0.1:%s/v1/backup'%s.server_port
            try:
                self.assertRaises(urllib.error.HTTPError,upload,url,key,encrypt_archive(key,b'invalid'))
                self.assertTrue(upload(url,key,encrypt_archive(key,archive(p,[('a','file')]))))
            finally: s.shutdown(); t.join(); s.server_close()
