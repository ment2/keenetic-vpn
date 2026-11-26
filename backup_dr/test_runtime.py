import tempfile,unittest,pathlib,hashlib
from runtime import tick
class Runtime(unittest.TestCase):
    def test_persistent_delay_retry_same_ciphertext(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d); (root/'source').write_text('v1'); work=root/'state'; args=(work,root,[('source','file')],bytes(32),'http://fixture'); calls=[]
            def fail(url,key,blob): calls.append(blob); raise OSError('network')
            def ok(url,key,blob): calls.append(blob); return hashlib.sha256(blob).hexdigest()
            self.assertEqual(tick(*args,now=100,send=ok),'idle'); self.assertEqual(tick(*args,now=3699,send=ok),'idle'); self.assertEqual(calls,[])
            with self.assertRaises(OSError): tick(*args,now=3700,send=fail)
            self.assertTrue((work/'pending.envelope').exists()); self.assertEqual(tick(*args,now=3701,send=ok),'accepted'); self.assertEqual(calls[0],calls[1]); self.assertFalse((work/'pending.envelope').exists()); self.assertEqual(tick(*args,now=9999,send=ok),'idle'); self.assertEqual(len(calls),2)
            (root/'source').write_text('v2'); self.assertEqual(tick(*args,now=10000,send=ok),'idle'); self.assertEqual(tick(*args,now=13600,send=ok),'accepted'); self.assertEqual(len(calls),3)
