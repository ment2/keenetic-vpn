import json, pathlib, tempfile, unittest, os
from provision import generate,wrap,unwrap,write_secret,confirmation
from monitor import status,publish
class ProvisionMonitor(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.private,cls.public=generate()
    def test_wrapped_master(self):
        master=os.urandom(32); ciphertext=wrap(self.public,master); self.assertEqual(unwrap(self.private,ciphertext),master); self.assertNotIn(master,ciphertext)
        self.assertRaises(ValueError,unwrap,self.private,ciphertext[:-1]+bytes([ciphertext[-1]^1]))
    def test_secret_permissions(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'key'; write_secret(p,bytes(32)); self.assertEqual(p.stat().st_mode & 0o777,0o600); self.assertRaises(FileExistsError,write_secret,p,bytes(32))
    def test_confirmation(self): self.assertNotEqual(confirmation(bytes(32),bytes(32)),confirmation(bytes(32),bytes([1])*32))
    def test_monitor(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d); root=p/'archive'; root.mkdir(); self.assertEqual(status(root,now=100,reserve=0)['status'],'awaiting_first_backup'); (root/('a'*64+'.gcm')).write_bytes(b'123'); record=status(root,now=101,reserve=0); publish(p/'status.json',record); self.assertEqual(json.loads((p/'status.json').read_text())['archive_bytes'],3); self.assertEqual(record['status'],'ready')
