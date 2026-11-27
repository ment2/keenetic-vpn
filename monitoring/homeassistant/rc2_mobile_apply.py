"""Apply reviewed RC2 page through supported Lovelace API only."""
import os,sys,json,time,copy,pathlib,yaml,urllib.request,re
sys.path.insert(0,"/data/ha-admin-agent")
from rc2_acceptance import WS,digest,BASE
def rest(path,body=None):
    q=urllib.request.Request("http://supervisor/core/api/"+path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization":"Bearer "+os.environ["SUPERVISOR_TOKEN"],"Content-Type":"application/json"})
    with urllib.request.urlopen(q,timeout=12) as r:return r.read().decode()
def render(t):return rest("template",{"template":t})
def main():
    cards=yaml.safe_load((BASE/"rc2_mobile_page.yaml").read_text())
    old=yaml.safe_load((BASE/"rc2_card_compact.yaml").read_text())
    graphs=yaml.safe_load((BASE/"rc2_history_cards.yaml").read_text())
    assert len(cards)==5 and len(graphs)==6
    state=json.loads(rest("states/sensor.keenetic_dynamic_vpn_rc2"))
    rows=state["attributes"]["rows"]
    assert state["state"]=="ok" and 0<=time.time()-state["attributes"]["checked_at"]<=150
    # Verify actual rendered Markdown lines and per-node graph selection.
    summary=render(cards[0]["content"]);table=render(cards[1]["content"]);detail=render(cards[4]["content"])
    lines=[x for x in table.splitlines() if x.startswith("|")]
    assert len(lines)==len(rows)+2 and all(x.count("|")==6 for x in lines)
    assert all(r["tag"] in lines[i+2] and r["tag"] in detail for i,r in enumerate(rows))
    plots=json.loads(render(cards[2]["filter"]["template"]))
    active=[r["tag"] for r in rows if r["active"] is True]
    assert [p["entities"][0]["name"] for p in plots]==active
    assert "Проверено:" in summary
    print("RENDER_PASS",len(rows),"table_lines",len(lines),"active_graphs",len(plots),flush=True)
    w=WS()
    try:
        cfg=w.call("lovelace/config",url_path="vpn-monitor")
        desired=copy.deepcopy(cfg)
        found={v.get("path"):i for i,v in enumerate(cfg["views"]) if v.get("path") in ("vpn-openai","rc2-shadow")}
        assert set(found)=={"vpn-openai","rc2-shadow"} and len(found)==2
        si=found["rc2-shadow"];li=found["vpn-openai"]
        new=cards[:4]+graphs+[cards[4]]
        if all(cfg["views"][i]["cards"]==new for i in found.values()):
            print("ALREADY_MATCHES");return
        assert digest(cfg)=="f9fb23b0f1017e4d91da460fb9cd990ce1861feeba3a12a41317234e4e89e3fc","dashboard changed; inspect first"
        assert cfg["views"][si]["cards"]==[old]+graphs
        assert cfg["views"][li]["cards"][0]["title"]=="Сводка по VPN"
        backup=BASE/("rc2-before-mobile-page-"+str(int(time.time()))+".json")
        payload=json.dumps(cfg,ensure_ascii=False,indent=2).encode()
        with os.fdopen(os.open(backup,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),"wb") as f:
            f.write(payload);f.flush();os.fsync(f.fileno())
        assert backup.read_bytes()==payload
        for i in found.values():desired["views"][i]["cards"]=copy.deepcopy(new)
        # Both existing URLs show the new page. Keep all other view metadata.
        assert digest(w.call("lovelace/config",url_path="vpn-monitor"))==digest(cfg)
        w.call("lovelace/config/save",url_path="vpn-monitor",config=desired)
        actual=w.call("lovelace/config",url_path="vpn-monitor")
        assert digest(actual)==digest(desired)
        print("PAGE_SAVED","views",sorted(found),"cards_per_view",len(new),"other_views_unchanged",all(v==actual["views"][j] for j,v in enumerate(cfg["views"]) if j not in found.values()),"backup",backup.name,flush=True)
    finally:w.close()
if __name__=="__main__":main()
