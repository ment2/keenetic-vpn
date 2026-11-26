import json,pathlib,tempfile,hashlib,unittest
from install_gate import verify_bundle,check_plan
class InstallGate(unittest.TestCase):
    def test_digest(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d); (p/'a').write_bytes(b'a'); (p/'bundle-manifest.json').write_text(json.dumps({'version':1,'files':{'a':hashlib.sha256(b'a').hexdigest()}})); self.assertEqual(verify_bundle(p),1); (p/'a').write_bytes(b'b'); self.assertRaises(ValueError,verify_bundle,p)
    def test_policy_not_authorization(self):
        policy=json.loads(pathlib.Path(__file__).with_name('group-policy-v3.3.json').read_text()); r=check_plan(policy); self.assertFalse(r['allowlist_verified']); self.assertFalse(r['installation_authorized']); self.assertEqual(r['configured_budget'],2*1024**3)
        self.assertRaises(ValueError,check_plan,policy,{'telegram-code':[['a','file']]},'/tmp')
