"""RC2 private LAN telemetry. No updater, Xray, firewall or route writes."""
import argparse
import hashlib
import ipaddress
import json
import os
import re
import time
from pathlib import Path
from monitoring.dynamic_snapshot import read_config, atomic_cache, ACTIVE, PENDING, MAX_NODES, MAX_INPUT_AGE
from monitoring.vpn_inventory import inventory
from monitoring.rc2_probe import collect, ip_value, city_value

TOPIC="keenetic/vpn-monitor/v1/dynamic_rc2"
DISCOVERY="homeassistant/sensor/keenetic6059_dynamic_rc2/config"
CACHE="/opt/var/lib/vpn-monitor/rc2-probes.json"
FRESH=1800
LAST_GEO_AGE=86400
KINDS=("internet","openai","exit_ip","geo")
STATUSES={"ok","unknown","timeout","network_error","http_error","invalid_response","geo_unavailable"}


def generation(outbound):
    # Local-only equality witness; never publish this digest or raw settings.
    cfg={k:v for k,v in outbound.items() if k!="tag"}
    return hashlib.sha256(json.dumps(cfg,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def endpoint(outbound):
    server=outbound["settings"]["vnext"][0]
    host=server["address"]
    if not isinstance(host,str) or not 1<=len(host)<=253:
        raise ValueError("invalid endpoint")
    ip=ip_value(host)
    if ip:
        host=ip
    else:
        host=host.encode("idna").decode("ascii").lower().rstrip(".")
        if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?",host):
            raise ValueError("invalid endpoint")
    port=server["port"]
    if type(port) is not int or not 1<=port<=65535:
        raise ValueError("invalid port")
    return host,port


def node_map(config, entries):
    by_tag={o["tag"]:o for o in config["outbounds"] if o.get("protocol")=="vless"}
    return {e["node_id"]:by_tag[e["tag"]] for e in entries}


def pool(path,optional=False):
    try:
        cfg,entries=read_config(path)
        return {node:generation(o) for node,o in node_map(cfg,entries).items()}
    except FileNotFoundError:
        return {} if optional else None
    except (OSError,ValueError,TypeError,KeyError,AttributeError):
        return None


def read_full(path,now):
    # Read content and freshness from the same inode, even during atomic replacement.
    with Path(path).open() as f:
        stamp=int(os.fstat(f.fileno()).st_mtime)
        cfg=json.load(f)
    if not 0<=now-stamp<=MAX_INPUT_AGE:
        raise ValueError("stale subscription")
    entries=inventory(cfg)
    if not 1<=len(entries)<=MAX_NODES or len({e["tag"] for e in entries})!=len(entries):
        raise ValueError("invalid inventory")
    return cfg,entries,stamp


def read_cache(path):
    try:
        with open(path) as f:
            data=json.load(f)
        return data if isinstance(data,dict) else {}
    except (OSError,ValueError):
        return {}


def clean_obs(raw,kind,now,max_age=FRESH):
    if not isinstance(raw,dict):
        return {"status":"missing","at":None,"ms":None}
    stamp=raw.get("checked_at")
    if type(stamp) is not int:
        return {"status":"missing","at":None,"ms":None}
    if not 0<=now-stamp<=max_age:
        return {"status":"stale","at":stamp,"ms":None}
    status=raw.get("status")
    if not isinstance(status,str) or status not in STATUSES or (status=="ok" and raw.get("route_verified") is not True):
        status="unknown"
    ms=raw.get("duration_ms")
    if type(ms) is not int or not 0<=ms<=120000:
        ms=None
    obs={"status":status,"at":stamp,"ms":ms}
    if kind in ("exit_ip","geo") and status=="ok":
        ip=ip_value(raw.get("ip"))
        if not ip:
            obs["status"]="invalid_response"
        else:
            obs["ip"]=ip
            if kind=="geo":
                c=raw.get("country")
                obs["country"]=c if isinstance(c,str) and re.fullmatch("[A-Z]{2}",c) else None
                obs["city"]=city_value(raw.get("city"))
                if not obs["country"] and not obs["city"]:
                    obs["status"]="geo_unavailable"
    return obs


def update_cache(config,entries,results,old,now):
    mapped=node_map(config,entries)
    cache={}
    for node,o in mapped.items():
        gen=generation(o)
        prev=old.get(node,{})
        if not isinstance(prev,dict) or prev.get("generation")!=gen:
            prev={}
        obs=results.get(node,{})
        if not isinstance(obs,dict):
            obs={}
        geo=clean_obs(obs.get("geo"),"geo",now)
        ip=clean_obs(obs.get("exit_ip"),"exit_ip",now)
        last=obs.get("geo") if geo["status"]=="ok" else prev.get("last_geo")
        last_clean=clean_obs(last,"geo",now,LAST_GEO_AGE)
        if last_clean["status"]!="ok" or (ip["status"]=="ok" and ip.get("ip")!=last_clean.get("ip")):
            last=None
        cache[node]={"generation":gen,"observations":obs,"last_geo":last}
    return cache


def membership(node,gen,p):
    if p is None:
        return None
    if node not in p:
        return False
    return True


def snapshot(config,entries,active,pending,cache,now,subscription_at=None):
    mapped=node_map(config,entries)
    rows=[]
    complete=0
    for e in entries:
        node=e["node_id"]
        o=mapped[node]
        gen=generation(o)
        host,port=endpoint(o)
        data=cache.get(node,{})
        if not isinstance(data,dict) or data.get("generation")!=gen:
            data={}
        raw=data.get("observations",{})
        if not isinstance(raw,dict):
            raw={}
        obs={k:clean_obs(raw.get(k),k,now) for k in KINDS}
        if all(v["at"] is not None and v["status"]!="stale" for v in obs.values()):
            complete+=1
        ip=obs["exit_ip"]
        geo=obs["geo"]
        # Never attach geography from a different exit IP. If independent IP
        # service is unavailable, the geo service itself may witness an IP.
        current_ip=ip.get("ip") if ip["status"]=="ok" else geo.get("ip") if geo["status"]=="ok" else None
        ip_source="exit_ip" if ip["status"]=="ok" else "geo" if current_ip else None
        if geo["status"]=="ok" and current_ip!=geo.get("ip"):
            geo={"status":"ip_mismatch","at":geo["at"],"ms":geo["ms"]}
            obs["geo"]=geo
        last=clean_obs(data.get("last_geo"),"geo",now,LAST_GEO_AGE)
        if last["status"]!="ok" or (current_ip and current_ip!=last.get("ip")):
            last=None
        # A VPN is confirmed if any independent request has a positive
        # owned-route witness. Failure of all services is not proof of cause.
        positive=[v["at"] for v in obs.values() if v["status"]=="ok"]
        attempted=[v["at"] for v in obs.values() if v["at"] is not None and v["status"]!="stale"]
        vpn={"status":"ok" if positive else "not_confirmed" if attempted else "missing",
             "at":max(positive or attempted,default=None)}
        rows.append({"id":node,"tag":e["tag"],"host":host,"port":port,
                     "active":membership(node,gen,active),"pending":membership(node,gen,pending),
                     "active_config_matches":None if active is None or node not in active else active[node]==gen,
                     "pending_config_matches":None if pending is None or node not in pending else pending[node]==gen,
                     "vpn":vpn,"internet":obs["internet"],"openai":obs["openai"],
                     "exit_ip":current_ip,"exit_ip_at":obs[ip_source]["at"] if ip_source else None,
                     "exit_ip_source":ip_source,"geo":geo,
                     "last_geo":last if geo["status"]!="ok" else None})
    known=set(mapped)
    result={"schema":2,"checked_at":int(now),"inventory_status":"ok","count":len(rows),"rows":rows,
            "subscription_at":subscription_at,"probe_complete":complete,
            "active_unmatched":None if active is None else len(set(active)-known),
            "pending_unmatched":None if pending is None else len(set(pending)-known)}
    if len(json.dumps(result,separators=(",",":"),ensure_ascii=True).encode())>32768:
        raise ValueError("RC2 payload capacity exceeded")
    return result


def discovery():
    return {"name":"Keenetic dynamic VPN RC2","unique_id":"keenetic6059_dynamic_rc2",
            "default_entity_id":"sensor.keenetic_dynamic_vpn_rc2","state_topic":TOPIC,
            "value_template":"{{ value_json.inventory_status }}","json_attributes_topic":TOPIC,"expire_after":150}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("mode",choices=["probe","publish"])
    p.add_argument("--full",required=True)
    p.add_argument("--cache",default=CACHE)
    p.add_argument("--publish",action="store_true")
    a=p.parse_args()
    full=Path(a.full).resolve()
    if full in {Path(ACTIVE).resolve(),Path(PENDING).resolve()}:
        raise SystemExit("unfiltered subscription required")
    if a.mode=="probe":
        cfg,entries,subscription_at=read_full(full,time.time())
        results=collect(cfg,entries,deadline=time.monotonic()+600)
        now=time.time()
        cache=update_cache(cfg,entries,results,read_cache(a.cache),now)
        atomic_cache(a.cache,cache)
        if a.publish:
            from monitoring.rc2_history import publish_history
            publish_history(snapshot(cfg,entries,None,None,cache,now,subscription_at)["rows"])
        print("RC2_PROBE",len(results),len(entries))
        return
    now=time.time()
    try:
        cfg,entries,subscription_at=read_full(full,now)
        data=snapshot(cfg,entries,pool(ACTIVE),pool(PENDING,True),read_cache(a.cache),now,subscription_at)
    except (OSError,ValueError,TypeError,KeyError,AttributeError):
        data={"schema":2,"checked_at":int(now),"inventory_status":"unavailable","count":0,"rows":[]}
    if a.publish:
        from monitoring.mqtt_lan_publisher import publish_once,load_password
        kw=dict(host="192.168.0.169",port=1883,username="keenetic_monitor",
                password=load_password("/opt/etc/vpn-monitor/mqtt-password"),client_id="keenetic-vpn-rc2")
        publish_once(**kw,topic=DISCOVERY,payload=discovery(),retain=True)
        publish_once(**kw,topic=TOPIC,payload=data)
    print("RC2_SNAPSHOT",data["inventory_status"],data["count"])


if __name__=="__main__":
    try:
        main()
    except Exception as exc:
        print("RC2_FAILED",type(exc).__name__)
        raise SystemExit(1)
