"""Bounded on-demand isolated Xray VLESS health probes.

Uses existing xray_server_check.py, which creates an isolated temporary Xray and
terminates only that child. Does not call/change production Xray process.
No credential access unless explicitly invoked locally with --publish.
"""
import argparse
import importlib.util
import ipaddress
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from monitoring.vpn_inventory import inventory
from monitoring.mqtt_lan_publisher import publish_once, load_password

TAG = re.compile(r"^vpn[0-9]{2,3}$")
CODES = {"ok", "config_error", "xray_start_failed", "probe_failed", "unknown"}
def normalize_result(tag, node_id, raw, duration_s, now=None):
    if not isinstance(raw, dict):
        raw = {}
    raw_status = str(raw.get("status", "unknown"))
    status = "ok" if raw_status == "ok" else "failed"
    address = raw.get("ip") if status == "ok" else None
    try:
        if address is not None:
            address = str(ipaddress.ip_address(address))
    except ValueError:
        address = None
        status = "failed"
    country = raw.get("country_code") if status == "ok" else None
    if not isinstance(country,str) or not re.fullmatch("[A-Z]{2}",country):
        country = None
    return {
        "schema": 1,
        "node_id": node_id,
        "tag": tag,
        "status": status,
        "route_verified": status == "ok" and address is not None,
        "egress_ip": address,
        "country_code": country,
        "test_duration_ms": round(duration_s * 1000),
        "test_kind": "isolated_xray_http_egress",
        "checked_at": now or datetime.now(timezone.utc).isoformat(),
        "latency_is_rtt": False,
    }

def load_probe(path="/opt/bin/xray_server_check.py"):
    spec = importlib.util.spec_from_file_location("existing_xray_server_check",path)
    if spec is None or spec.loader is None:
        raise RuntimeError("probe script unavailable")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    if not callable(getattr(m,"probe",None)):
        raise RuntimeError("probe function missing")
    return m.probe

def probe_one(config, tag, probe_function):
    found = [o for o in config.get("outbounds",[]) if o.get("tag")==tag and o.get("protocol")=="vless"]
    if len(found)!=1:
        raise ValueError("unknown or duplicate VLESS tag")
    node = next(item for item in inventory(config) if item["tag"]==tag)
    start=time.monotonic()
    try:
        raw=probe_function(found[0])
    except Exception:
        raw={"status":"unknown"}
    return normalize_result(tag,node["node_id"],raw,time.monotonic()-start)

def execute(*, tag, config_path="/opt/etc/xray/config.json", publish=False,
            mqtt_password_path="/opt/etc/vpn-monitor/mqtt-password"):
    if not TAG.fullmatch(tag):
        raise ValueError("invalid tag")
    cfg=json.loads(Path(config_path).read_text())
    event=probe_one(cfg,tag,load_probe())
    if publish:
        passwd=load_password(mqtt_password_path)
        publish_once(
            host="192.168.0.169",port=1883,username="keenetic_monitor",password=passwd,
            topic=f"keenetic/vpn-monitor/v1/{event['node_id']}/health",payload=event)
    return event

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--tag",required=True)
    p.add_argument("--publish",action="store_true")
    a=p.parse_args()
    event=execute(tag=a.tag,publish=a.publish)
    print(json.dumps({**event, "mqtt_puback":bool(a.publish)},sort_keys=True))

if __name__=="__main__":
    main()
