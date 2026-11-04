import json
import unittest
from monitoring.xray_change_gate import decide

def conf(tags):
    return json.dumps({"outbounds":[{"tag":t,"protocol":"vless"} for t in tags],
     "routing":{"balancers":[{"tag":"auto","fallbackTag":tags[0]}]}}).encode()

class GateTests(unittest.TestCase):
    def test_identical_live_skips(self):
        a=conf(["vpn01"])
        self.assertEqual(decide(a,a,a)["decision"],"unchanged")
    def test_pending_matches_candidate_live_differs(self):
        live=conf(["vpn01","vpn06"])
        new=conf(["vpn01"])
        r=decide(live,new,new)
        self.assertEqual(r["decision"],"apply_required")
        self.assertTrue(r["pending_equal"])
    def test_new_candidate_requires_apply(self):
        self.assertEqual(decide(conf(["vpn01"]),conf(["vpn01","vpn02"]))["decision"],"apply_required")
    def test_empty_pool_rejected(self):
        self.assertEqual(decide(conf(["vpn01"]),conf([]))["decision"],"reject")
    def test_bad_fallback_rejected(self):
        a=json.loads(conf(["vpn01"]))
        a["routing"]["balancers"][0]["fallbackTag"]="vpn07"
        self.assertEqual(decide(conf(["vpn01"]),json.dumps(a).encode())["decision"],"reject")
    def test_reordered_json_is_semantically_unchanged(self):
        a=b'{"outbounds":[{"tag":"vpn01","protocol":"vless"}]}'
        b=b'{"outbounds":[{"protocol":"vless","tag":"vpn01"}]}'
        self.assertEqual(decide(a,b)["decision"],"unchanged")
if __name__=="__main__":unittest.main()
