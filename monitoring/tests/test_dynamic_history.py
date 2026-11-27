import unittest
from unittest.mock import Mock
from monitoring import dynamic_history as d

NODE="node_"+"a"*20
ROW=[NODE,"vpn03",False,False,"ok",100,123,"203.0.113.1","DE","reachable",101,456]

class HistoryTests(unittest.TestCase):
    def test_stable_ids_across_tag_changes(self):
        a=list(d.messages(NODE,"vpn03"))
        b=list(d.messages(NODE,"vpn09"))
        self.assertEqual(len(a),4)
        self.assertEqual([x[0] for x in a],[x[0] for x in b])
        self.assertEqual([x[1]["unique_id"] for x in a],[x[1]["unique_id"] for x in b])
        self.assertNotEqual(a[0][1]["name"],b[0][1]["name"])
    def test_sanitized_state(self):
        r=d.state_payload(ROW)
        self.assertEqual(r["vless"],"ok")
        self.assertEqual(r["openai"],"reachable")
        self.assertNotIn("ip",r)
        self.assertNotIn("203.0.113.1",str(r))
    def test_discovery_and_state(self):
        p=Mock()
        d.publish_history([ROW],publisher=p,password_reader=lambda _: "test-only")
        self.assertEqual(p.call_count,5)
        self.assertTrue(all(x.kwargs["retain"] for x in p.call_args_list[:4]))
        self.assertFalse(p.call_args.kwargs["retain"])
        self.assertEqual(p.call_args.kwargs["payload"]["node_id"],NODE)
    def test_invalid_identity(self):
        with self.assertRaises(ValueError):
            list(d.messages("wrong","vpn03"))
