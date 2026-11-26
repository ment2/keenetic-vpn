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

from recover_ha_queue import reconcile,local_fence,Client
import fcntl,urllib.error,io
from unittest.mock import patch
JOB='4d3a785f-b37a-4fe3-aaf9-3b30cce9becd'
class UnknownFake(Fake):
    def __init__(self):
        super().__init__(); self.job='unknown'; self.count=1; self.block=JOB
    def call(self,path,data=None,policy=None):
        if path=='/v1/recovery/status': return dict(generation=1 if self.count else 2,unresolved_count=self.count,blocked_job=self.block)
        if path=='/v1/jobs/'+JOB: return dict(id=JOB,status=self.job)
        if path=='/v1/owner/reconcile':
            self.posts+=1
            assert data=={'id':JOB,'action':'acknowledge_unknown_no_reexecute'}
            if self.fail: raise RecoveryError('POST_HTTP_403_CF_1010')
            self.job='failed';self.count=0;self.block=None;return {'ok':True}
        return super().call(path,data,policy)
class UnknownTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.c=UnknownFake()
    def test_exact_once(self):
        with local_fence(self.root): self.assertTrue(reconcile(self.c,self.root,'fixture',JOB,4))
        self.assertEqual(self.c.p['revision'],4)
        with self.assertRaises(RecoveryError): reconcile(self.c,self.root,'fixture',JOB,4)
        self.assertEqual(self.c.posts,1)
    def test_other_block(self):
        self.c.block='other'
        with self.assertRaisesRegex(RecoveryError,'NOT_SOLE'): reconcile(self.c,self.root,'fixture',JOB,4)
        self.assertEqual(self.c.posts,0)
    def test_multiple_unknown(self):
        self.c.count=2
        with self.assertRaisesRegex(RecoveryError,'NOT_SOLE'): reconcile(self.c,self.root,'fixture',JOB,4)
        self.assertEqual(self.c.posts,0)
    def test_pending(self):
        (self.root/'pending.json').touch()
        with self.assertRaisesRegex(RecoveryError,'PENDING'): reconcile(self.c,self.root,'fixture',JOB,4)
        self.assertEqual(self.c.posts,0)
    def test_live_lock(self):
        with local_fence(self.root):
            with self.assertRaisesRegex(RecoveryError,'RUNNING'): 
                with local_fence(self.root): pass
    def test_forbidden_no_retry(self):
        self.c.fail=True
        with self.assertRaisesRegex(RecoveryError,'CF_1010.*BEFORE_ANY_RETRY'): reconcile(self.c,self.root,'fixture',JOB,4)
        self.assertEqual(self.c.posts,1)
    def test_not_unknown(self):
        self.c.job='done'
        with self.assertRaisesRegex(RecoveryError,'NOT_UNKNOWN'): reconcile(self.c,self.root,'fixture',JOB,4)
        self.assertEqual(self.c.posts,0)
    def test_ua_and_1010(self):
        c=Client('synthetic')
        def deny(req,timeout):
            self.assertEqual(req.get_header('User-agent'),'ha-control-agent/0.1-candidate')
            raise urllib.error.HTTPError(req.full_url,403,'Forbidden',{},io.BytesIO(b'error code: 1010'))
        with patch.object(c.opener,'open',side_effect=deny):
            with self.assertRaisesRegex(RecoveryError,'POST_HTTP_403_CF_1010'): c.call('/v1/owner/reconcile',{'id':JOB},'fixture')
