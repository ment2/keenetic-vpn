import json
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from types import SimpleNamespace
import yaml
from jinja2 import Environment, StrictUndefined

ROOT=Path(__file__).resolve().parents[1]/"homeassistant"
NOW=1795788000
N1="node_"+"a"*20
N2="node_"+"b"*20
ROWS=[[N1,"vpn01",True,False,"ok",NOW-10,15,"203.0.113.1","DE","reachable",NOW-10,20,"new.example.invalid",443,"ok",NOW-10,"Berlin",30],
      [N2,"vpn10",False,True,"ok",NOW-1801,15,"203.0.113.2","DE","reachable",NOW-1801,20,"old.example.invalid",443,"stale",NOW-1801,"Paris",30]]

class States:
    def __init__(self,status,entities):
        self.status=status
        self.sensor=entities
    def __call__(self,entity):
        return self.status

def render(template,rows=ROWS,stamp=NOW,status="ok",entities=()):
    attrs={"schema":2,"rows":rows,"checked_at":stamp,"active_unmatched":0,"pending_unmatched":0}
    env=Environment(undefined=StrictUndefined)
    env.filters["to_json"]=json.dumps
    return env.from_string(template).render(
        states=States(status,entities),state_attr=lambda e,k:attrs.get(k),
        now=lambda:datetime.fromtimestamp(NOW,timezone.utc),
        as_timestamp=lambda d:d.timestamp(),
        as_datetime=lambda n:datetime.fromtimestamp(n,timezone.utc),
        as_local=lambda d:d.astimezone(timezone(timedelta(hours=3))))

class HATemplates(unittest.TestCase):
    def test_mobile_stale_and_fresh(self):
        template=yaml.safe_load((ROOT/"dynamic_vpn_card.yaml").read_text())["content"]
        result=render(template)
        self.assertIn("Всего: 2",result)
        self.assertIn("активных: 1",result)
        self.assertIn("pending: 1",result)
        self.assertIn("VPN / Интернет: 1/2",result)
        self.assertIn("vpn10",result)
        self.assertIn("нет свежих данных",result)
        self.assertIn("203.0.113.2",result)
        self.assertIn("устарела",result)
        self.assertIn("new.example.invalid:443",result)
        self.assertIn("Berlin",result)
        self.assertIn("Paris",result)
        self.assertIn("Нет актуального списка",render(template,stamp=NOW-151))
    def test_history_only_current_identity_and_metric(self):
        cards=yaml.safe_load((ROOT/"dynamic_history_cards.yaml").read_text())
        self.assertEqual(len(cards),4)
        for card,metric in zip(cards,("vless","openai","vless_ms","openai_ms")):
            entities=[SimpleNamespace(entity_id="sensor.keenetic_rc2_new",attributes={"node_id":N1,"metric":metric}),
                      SimpleNamespace(entity_id="sensor.keenetic_rc2_old",attributes={"node_id":"node_"+"c"*20,"metric":metric}),
                      SimpleNamespace(entity_id="sensor.keenetic_rc2_wrong",attributes={"node_id":N1,"metric":"other"})]
            template=card["filter"]["template"]
            self.assertEqual(json.loads(render(template,entities=entities)),[{"entity":"sensor.keenetic_rc2_new","name":"vpn01"}])
            self.assertEqual(json.loads(render(template,stamp=NOW-151,entities=entities)),[])
