import pathlib,tempfile,unittest,concurrent.futures,shutil
from transport import store
from quota import QuotaExceeded
from global_quota import usage
class GlobalQuota(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=pathlib.Path(self.tmp.name)
        self.a=self.root/'a'; self.b=self.root/'b'; self.retired=self.root/'retired'
        for p in (self.a,self.b,self.retired): p.mkdir(mode=0o700)
    def tearDown(self): self.tmp.cleanup()
    def put(self,p,data,budget=10,reserve=0): return store(p,data,100,reserve,global_root=self.root,global_budget=budget)
    def test_retired_and_pending_count(self):
        (self.retired/'old').write_bytes(b'1234'); (self.a/'.pending-crash').write_bytes(b'12')
        self.put(self.b,b'1234'); self.assertEqual(usage(self.root),10)
        with self.assertRaises(QuotaExceeded): self.put(self.a,b'1')
        self.assertEqual((self.retired/'old').read_bytes(),b'1234')
    def test_duplicate_at_capacity(self):
        d=self.put(self.a,b'1234567890'); self.assertEqual(self.put(self.a,b'1234567890'),d); self.assertEqual(usage(self.root),10)
    def test_parallel_global_admission(self):
        def go(p):
            try: self.put(p,b'123456'); return True
            except QuotaExceeded: return False
        with concurrent.futures.ThreadPoolExecutor(2) as ex: self.assertEqual(sum(ex.map(go,(self.a,self.b))),1)
    def test_reserve_and_symlink(self):
        with self.assertRaises(QuotaExceeded): self.put(self.a,b'1',reserve=shutil.disk_usage(self.root).free)
        (self.retired/'link').symlink_to('/tmp')
        with self.assertRaises(ValueError): self.put(self.a,b'1')
