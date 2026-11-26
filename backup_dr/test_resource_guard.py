import pathlib,tempfile,unittest
from resource_guard import check_memory
from snapshot import archive
class ResourceGuard(unittest.TestCase):
    def test_low_memory(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'meminfo'; p.write_text('MemAvailable: 60000 kB\n'); self.assertRaises(MemoryError,check_memory,p); p.write_text('MemAvailable: 80000 kB\n'); self.assertEqual(check_memory(p),80000*1024)
    def test_source_budget(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d); (p/'a').write_bytes(b'1234'); self.assertRaises(ValueError,archive,p,[('a','file')],3)
