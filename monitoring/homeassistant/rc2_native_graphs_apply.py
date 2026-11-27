"""Replace custom graph cards with built-in Home Assistant history-graph.
Dashboard only. Uses real registry entities from current RC2 snapshot.
No HACS/resource changes and no router operation.
"""
import os,sys,json,time,copy,pathlib,urllib.request
sys.path.insert(0,"/data/ha-admin-agent")
from rc2_acceptance import WS,digest,BASE
def rest(path):
 q=urllib.request.Request("http://supervisor/core/api/"+path,headers={"Authorization":"Bearer "+os.environ["SUPERVISOR_TOKEN"]})
 with urllib.request.urlopen(q,timeout=12) as r:return json.load(r)
def make_graphs(rows,states):
 by={}
 for s in states:
  a=s.get("attributes",{});eid=s["entity_id"]
  if not eid.startswith("sensor.keenetic_rc2_"):continue
  key=(a.get("node_id"),a.get("metric"))
  if key[0] and key[1]:
   if key in by:raise RuntimeError("duplicate history sensor")
   by[key]=eid
 metrics=("vpn","internet","openai","geo","internet_ms","openai_ms")
 assert len({r["id"] for r in rows})==len(rows)>0
 assert all((r["id"],m) in by for r in rows for m in metrics),"missing metric"
 ordered=sorted(rows,key=lambda r:int(r["tag"][3:]))
 def entity(r,m,name=None):return {"entity":by[(r["id"],m)],"name":name or r["tag"]}
 def graph(title,hours,entities):return {"type":"history-graph","title":title,"hours_to_show":hours,"entities":entities}
 # Native graph cards show the entire current subscription, not a stale
 # hardcoded active-pool list. Membership is live in the separate table.
 individual=[graph(r["tag"]+" · время HTTP-пробы, мс · 6 ч",6,[entity(r,"internet_ms","Интернет"),entity(r,"openai_ms","OpenAI")]) for r in ordered]
 labels={"vpn":"VPN","internet":"Интернет","openai":"OpenAI","geo":"Геолокация","internet_ms":"Интернет, время пробы","openai_ms":"OpenAI, время пробы"}
 historical=[graph(labels[m]+" · 24 ч",24,[entity(r,m) for r in ordered]) for m in metrics]
 return individual,historical
def main():
 allstates=rest("states")
 state=next(s for s in allstates if s["entity_id"]=="sensor.keenetic_dynamic_vpn_rc2")
 a=state["attributes"];rows=a["rows"]
 assert state["state"]=="ok" and 0<=time.time()-a["checked_at"]<=150
 individual,historical=make_graphs(rows,allstates)
 print("NATIVE_GRAPHS",len(individual),"HISTORY",len(historical),"ENTITIES",len(rows)*6,flush=True)
 w=WS()
 try:
  cfg=w.call("lovelace/config",url_path="vpn-monitor")
  desired=copy.deepcopy(cfg)
  found=[i for i,v in enumerate(cfg["views"]) if v.get("path") in ("vpn-openai","rc2-shadow")]
  assert len(found)==2
  for i in found:
   cards=cfg["views"][i]["cards"]
   assert len(cards)==11 and [c["type"] for c in cards]==["markdown","markdown","custom:auto-entities","markdown"]+["custom:auto-entities"]*6+["markdown"],"unexpected page shape"
   assert [cards[j]["title"] for j in (0,1,3,10)]==["Сводка RC2","Серверы VPN","Как читать графики","Подробности серверов"]
   note=copy.deepcopy(cards[3])
   note["content"]="Графики всех текущих серверов подписки за 6 часов. Новая HTTP-проба каждые 15 минут; сводка каждую минуту. Графики расположены по номеру VPN; актуальное членство в пуле см. в таблице. При изменении состава подписки список графиков нужно обновить. Время HTTP-пробы (включая ожидание ошибок), не ICMP ping. Интернет — HTTP 204, OpenAI — HTTP 401."
   desired["views"][i]["cards"]=cards[:2]+individual+[note]+historical+[cards[10]]
  assert digest(cfg)=="c955bcb4d61a7e769f6c5d59512984bf7650a4222c62c6e30b5084888d9f0058","dashboard changed"
  backup=BASE/("rc2-before-native-graphs-"+str(int(time.time()))+".json")
  payload=json.dumps(cfg,ensure_ascii=False,indent=2).encode()
  with os.fdopen(os.open(backup,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),"wb") as f:
   f.write(payload);f.flush();os.fsync(f.fileno())
  assert backup.read_bytes()==payload
  assert digest(w.call("lovelace/config",url_path="vpn-monitor"))==digest(cfg)
  w.call("lovelace/config/save",url_path="vpn-monitor",config=desired)
  actual=w.call("lovelace/config",url_path="vpn-monitor")
  assert digest(actual)==digest(desired)
  assert all(not any(c["type"].startswith("custom:") for c in actual["views"][i]["cards"]) for i in found)
  print("NATIVE_SAVED",len(found),"cards_per_view",len(desired["views"][found[0]]["cards"]),"backup",backup.name,flush=True)
 finally:w.close()
if __name__=="__main__":main()
