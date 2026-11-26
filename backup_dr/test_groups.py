import pathlib,tempfile,unittest
from groups import validate,preflight,group_key,config_id
class Groups(unittest.TestCase):
    def test_validate(self):
        self.assertEqual(validate({'xray':[['b','file'],['a','sqlite']]}),{'xray':[('a','sqlite'),('b','file')]})
        for bad in ({'../x':[['a','file']]},{'x':[['../a','file']]},{'x':[['a','file']],'y':[['a','sqlite']]},{'x':[]},{'x':[['a','log']]}):
            with self.assertRaises(ValueError): validate(bad)
    def test_preflight(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d); (p/'a').write_bytes(b'a'*4); (p/'b').write_bytes(b'b'*8); (p/'link').symlink_to('a'); (p/'db').write_bytes(b'd'*4); (p/'db-wal').write_bytes(b'w'*8)
            r=preflight(p,{'good':[['a','file']],'large':[['b','file']],'bad':[['link','file']],'missing':[['gone','file']],'sqlite':[['db','sqlite']]},limit=6)
            self.assertTrue(r['good']['ready']); self.assertFalse(any(r[g]['ready'] for g in ('large','bad','missing','sqlite'))); self.assertEqual(r['sqlite']['estimated_bytes'],12)
    def test_isolation(self):
        k=bytes(32); self.assertNotEqual(group_key(k,'xray'),group_key(k,'bot')); self.assertEqual(group_key(k,'xray'),group_key(k,'xray')); self.assertEqual(config_id([('a','file'),('b','sqlite')]),config_id([('b','sqlite'),('a','file')]))
