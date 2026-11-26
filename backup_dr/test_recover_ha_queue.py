import tempfile,unittest
from pathlib import Path
from recover_ha_queue import recover,RecoveryError,SCOPES

class Fake:
    def __init__(self):
        self.p=dict(revision=4,authority='durable_object',remote_enabled=True,owner_admin_enabled=True,scopes=sorted(SCOPES)); self.events=[]; self.posts=0; self.fail=False
    def call(self,path,data=None,policy=None):
        if path=='/v1/permissions': return dict(self.p)
        if path=='/v1/audit': return {'events':self.events}
        self.posts+=1
        if self.fail: raise RecoveryError('POST_HTTP_401')
        assert data=={k:self.p[k] for k in data}; self.p['revision']+=1
        return {'ok':True,'revision':self.p['revision']}
class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.root=Path(self.tmp.name); self.c=Fake()
    def test_reset_once_preserves_policy(self):
        self.assertEqual(recover(self.c,self.root,'fixture',4),5); self.assertEqual(self.c.posts,1)
        with self.assertRaisesRegex(RecoveryError,'REVISION_CHANGED'): recover(self.c,self.root,'fixture',4)
        self.assertEqual(self.c.posts,1)
    def test_pending_blocks(self):
        (self.root/'pending.json').touch()
        with self.assertRaisesRegex(RecoveryError,'PENDING'): recover(self.c,self.root,'fixture',4)
        self.assertEqual(self.c.posts,0)
    def test_claim_blocks(self):
        self.c.events=[{'job_id':'x','event':'claimed'}]
        with self.assertRaisesRegex(RecoveryError,'RUNNING_OR_UNKNOWN'): recover(self.c,self.root,'fixture',4)
        self.assertEqual(self.c.posts,0)
    def test_post_error_no_retry(self):
        self.c.fail=True
        with self.assertRaisesRegex(RecoveryError,'POST_HTTP_401.*BEFORE_ANY_RETRY'): recover(self.c,self.root,'fixture',4)
        self.assertEqual(self.c.posts,1)
    def test_result_resolves_claim(self):
        self.c.events=[{'job_id':'x','event':'result_received'},{'job_id':'x','event':'claimed'}]
        self.assertEqual(recover(self.c,self.root,'fixture',4),5)
