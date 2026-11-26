import os,pathlib,tempfile,unittest
from retention import prune
from transport import encrypt_archive,store
class Retention(unittest.TestCase):
    def test_keep_two_and_unknown(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d); key=bytes(32); paths=[]
            for i in range(3):
                p=root/(store(root,encrypt_archive(key,str(i).encode()))+'.gcm'); os.utime(p,(100+i,100+i)); paths.append(p)
            unknown=root/('0'*64+'.gcm'); unknown.write_bytes(b'unknown')
            self.assertEqual(prune(root,key,now=40*86400),[paths[0].name]); self.assertTrue(paths[1].exists()); self.assertTrue(paths[2].exists()); self.assertTrue(unknown.exists())
