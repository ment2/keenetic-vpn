"""RC2 stable-ID history sensors. Private LAN only."""
import re
from monitoring.mqtt_lan_publisher import publish_once,load_password

METRICS={"vpn":"VPN witness","internet":"Internet HTTP 204","openai":"OpenAI HTTP 401",
         "geo":"Geolocation","internet_ms":"Internet probe duration","openai_ms":"OpenAI probe duration"}
NODE=re.compile(r"node_[a-f0-9]{20}")
TAG=re.compile(r"vpn[0-9]{2,3}")


def messages(node,tag):
    if not NODE.fullmatch(node) or not TAG.fullmatch(tag):
        raise ValueError("invalid identity")
    topic=f"keenetic/vpn-monitor/v1/{node}/rc2_history"
    for metric,label in METRICS.items():
        uid=f"keenetic6059_rc2_{node}_{metric}"
        payload={"name":f"{tag} {label}","unique_id":uid,
                 "default_entity_id":f"sensor.keenetic_rc2_{node}_{metric}",
                 "state_topic":topic,"value_template":"{{ value_json."+metric+" }}",
                 "expire_after":1800,"json_attributes_topic":topic,
                 "json_attributes_template":'{{ {"node_id": value_json.node_id, "metric": "'+metric+'"} | to_json }}'}
        if metric.endswith("_ms"):
            payload["unit_of_measurement"]="ms"
        yield f"homeassistant/sensor/{uid}/config",payload


def state_payload(row):
    node,tag=row["id"],row["tag"]
    if not NODE.fullmatch(node) or not TAG.fullmatch(tag):
        raise ValueError("invalid identity")
    return {"node_id":node, "tag":tag, **{k:row[k]["status"] for k in ("vpn","internet","openai","geo")},
            "internet_ms":row["internet"]["ms"],"openai_ms":row["openai"]["ms"]}


def publish_history(rows,*,publisher=publish_once,password_reader=load_password):
    password=password_reader("/opt/etc/vpn-monitor/mqtt-password")
    kw=dict(host="192.168.0.169",port=1883,username="keenetic_monitor",
            password=password,client_id="keenetic-vpn-rc2-history")
    for row in rows:
        node,tag=row["id"],row["tag"]
        for topic,payload in messages(node,tag):
            publisher(**kw,topic=topic,payload=payload,retain=True)
        publisher(**kw,topic=f"keenetic/vpn-monitor/v1/{node}/rc2_history",
                  payload=state_payload(row),retain=False)
