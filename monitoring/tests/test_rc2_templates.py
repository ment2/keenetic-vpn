import json
import unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from types import SimpleNamespace
import yaml
from jinja2 import Environment,StrictUndefined
from monitoring import rc2_snapshot as s
from monitoring.tests.test_rc2 import NOW,config,outbound,sample,event,row

ROOT=Path(__file__).resolve().parents[1]/"homeassistant"
class States:
    def __init__(self,status,entities):
        self.status=status
        self.sensor=entities
    def __call__(self,e):
        return self.status

def render(template,rows,*,stamp=NOW,status="ok",entities=()):
    attrs={"rows":rows,"checked_at":stamp,"active_unmatched":0,"pending_unmatched":0}
    env=Environment(undefined=StrictUndefined)
    env.filters["to_json"]=json.dumps
    return env.from_string(template).render(states=States(status,entities),
        state_attr=lambda e,k:attrs.get(k),now=lambda:datetime.fromtimestamp(NOW,timezone.utc),
        as_timestamp=lambda d:d.timestamp(),as_datetime=lambda n:datetime.fromtimestamp(n,timezone.utc),
        as_local=lambda d:d.astimezone(timezone(timedelta(hours=3))))

class RC2Templates(unittest.TestCase):
    def test_mobile_independent_status_and_geo(self):
        template=yaml.safe_load((ROOT/"rc2_card.yaml").read_text())["content"]
        cfg=config(outbound()); _,cache=row(cfg,sample())
        r,_=row(cfg,{"internet":event(),"openai":event(),"exit_ip":event(ip="203.0.113.1"),"geo":event("network_error")},cache)
        out=render(template,[r])
        self.assertIn("VPN: 1/1",out)
        self.assertIn("OpenAI: 1/1",out)
        self.assertIn("🟢 Сеть: OK",out)
        self.assertIn("🔴 GEO: сбой сети",out)
        self.assertIn("Последняя известная (устарела): DE / Frankfurt",out)
        self.assertIn("one.example.invalid:443",out)
        self.assertIn("203.0.113.1",out)
        self.assertIn("Нет актуальной подписки",render(template,[r],stamp=NOW-151))
    def test_mobile_current_geo_and_ip_change(self):
        template=yaml.safe_load((ROOT/"rc2_card.yaml").read_text())["content"]
        r,_=row(config(outbound()),sample())
        self.assertIn("DE / Frankfurt",render(template,[r]))
        obs=sample(); obs["exit_ip"]=event(ip="203.0.113.2")
        r,_=row(config(outbound()),obs)
        out=render(template,[r])
        self.assertIn("IP не совпали",out)
        self.assertNotIn("Frankfurt",out)
    def test_mobile_matrix_rows_and_short_labels(self):
        template=yaml.safe_load((ROOT/"rc2_card.yaml").read_text())["content"]
        cfg=config(*[outbound("vpn%02d"%i,"host%d.example.invalid"%i) for i in range(1,11)])
        entries=s.inventory(cfg)
        cache=s.update_cache(cfg,entries,{e["node_id"]:sample() for e in entries},{},NOW)
        rows=s.snapshot(cfg,entries,{}, {},cache,NOW)["rows"]
        out=render(template,rows)
        lines=out.splitlines()
        start=next(i for i,v in enumerate(lines) if v.startswith("| Сервер"))
        self.assertTrue(lines[start+1].startswith("| :---"))
        self.assertEqual(len([v for v in lines[start+2:start+12] if v.startswith("|")]),10)
        self.assertIn("vpn10",lines[start+11])
        self.assertNotIn("network_error",out)
    def test_history_current_ids(self):
        cards=yaml.safe_load((ROOT/"rc2_history_cards.yaml").read_text())
        r,_=row(config(outbound()),sample())
        self.assertEqual(len(cards),6)
        for card,metric in zip(cards,("vpn","internet","openai","geo","internet_ms","openai_ms")):
            entities=[SimpleNamespace(entity_id="sensor.keenetic_rc2_new",attributes={"node_id":r["id"],"metric":metric}),
                      SimpleNamespace(entity_id="sensor.keenetic_rc2_old",attributes={"node_id":"node_"+"b"*20,"metric":metric})]
            result=json.loads(render(card["filter"]["template"],[r],entities=entities))
            self.assertEqual(result,[{"entity":"sensor.keenetic_rc2_new","name":"vpn01"}])
