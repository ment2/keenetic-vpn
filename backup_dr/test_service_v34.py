import json, os, pathlib, tempfile, unittest, stat
from service_v34 import load_plan, local_master, exclusive, maintenance, run_receiver
from snapshot import archive
from transport import encrypt_archive,store
from groups import group_key
from group_runtime import make_receiver

class Service(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=pathlib.Path(self.tmp.name)
        self.key=bytes(range(32)); self.config={'alpha':[['a','file']]}; self.quotas={'alpha':100000}
    def tearDown(self): self.tmp.cleanup()
    def test_plan_and_key(self):
        p=self.root/'plan'; p.write_text(json.dumps({'version':1,'groups':self.config,'quotas':self.quotas}))
        self.assertEqual(load_plan(p)[1],self.quotas)
        k=self.root/'key'; k.write_bytes(self.key); k.chmod(0o600); self.assertEqual(local_master(k),self.key)
        k.chmod(0o644)
        with self.assertRaises(ValueError): local_master(k)
        link=self.root/'link'; link.symlink_to(k)
        with self.assertRaises(OSError): local_master(link)
    def test_lock(self):
        p=self.root/'lock'
        with exclusive(p):
            with self.assertRaises(BlockingIOError):
                with exclusive(p): pass
    def test_retention_rejects_nonmanifest(self):
        dest=self.root/'dest'; dest.mkdir(mode=0o700); g=dest/'alpha'; g.mkdir(mode=0o700); k=group_key(self.key,'alpha')
        valid=[]
        for i in range(3):
            (self.root/'a').write_text(str(i)); p=g/(store(g,encrypt_archive(k,archive(self.root,[('a','file')])))+'.gcm'); os.utime(p,(100+i,100+i)); valid.append(p)
        invalid=g/(store(g,encrypt_archive(k,b'invalid'))+'.gcm'); os.utime(invalid,(1,1))
        self.assertEqual(maintenance(dest,self.config,self.key,now=40*86400),{'alpha':1})
        self.assertFalse(valid[0].exists()); self.assertTrue(all(p.exists() for p in valid[1:])); self.assertTrue(invalid.exists())
    def test_heartbeat_shutdown(self):
        dest=self.root/'dest'; srv=make_receiver(dest,self.key,self.config,self.quotas,'127.0.0.1',('127.0.0.1',0),reserve=0)
        path=self.root/'status'; run_receiver(srv,dest,self.config,self.key,path,stop=lambda:path.exists(),reserve=0)
        r=json.loads(path.read_text()); self.assertEqual(r['status'],'awaiting_first_backup'); self.assertFalse(r['retention_error']); self.assertEqual(srv.socket.fileno(),-1)
    def test_group_body_limit(self):
        import http.client, threading
        from resource_guard import CIPHER_MAX
        dest=self.root/'dest'; srv=make_receiver(dest,self.key,self.config,self.quotas,'127.0.0.1',('127.0.0.1',0),reserve=0)
        t=threading.Thread(target=srv.serve_forever); t.start()
        try:
            c=http.client.HTTPConnection('127.0.0.1',srv.server_port,timeout=3)
            c.putrequest('POST','/v1/backup/alpha'); c.putheader('Content-Length',str(CIPHER_MAX+1)); c.endheaders()
            self.assertEqual(c.getresponse().status,400); c.close()
            self.assertEqual(list((dest/'alpha').iterdir()),[])
        finally: srv.shutdown(); t.join(); srv.server_close()
