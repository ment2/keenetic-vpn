import unittest,json,os
from escrow import envelope,recover,fingerprint,master_id
from provision import generate
from groups import group_key
from transport import encrypt_archive,keys
from crypto import open_sealed
class Escrow(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.private,cls.public=generate(); cls.other_private,cls.other_public=generate()
    def test_offline_restore(self):
        key=os.urandom(32); fp=fingerprint(self.public); mid=master_id(key); raw=envelope(self.public,key,fp)
        blob=encrypt_archive(group_key(key,'fixture'),b'synthetic backup')
        self.assertNotIn(key,raw); recovered=recover(self.private,raw,fp,mid)
        self.assertEqual(open_sealed(keys(group_key(recovered,'fixture'))[0],blob),b'synthetic backup')
    def test_wrong_recipient(self):
        key=os.urandom(32); fp=fingerprint(self.public); mid=master_id(key); raw=envelope(self.public,key,fp)
        with self.assertRaises(ValueError): envelope(self.other_public,key,fp)
        with self.assertRaises(ValueError): recover(self.other_private,raw,fp,mid)
        with self.assertRaises(ValueError): recover(self.private,raw,fp,master_id(os.urandom(32)))
    def test_tamper(self):
        key=os.urandom(32); fp=fingerprint(self.public); mid=master_id(key); e=json.loads(envelope(self.public,key,fp)); e['wrapped']='AAAA'
        with self.assertRaises(ValueError): recover(self.private,json.dumps(e).encode(),fp,mid)
