"""Monitor-only history sensors. No credentials or raw configuration in MQTT."""
import re
from monitoring.mqtt_lan_publisher import publish_once, load_password

METRICS = {"vless":("VLESS status",None), "openai":("OpenAI status",None),
           "vless_ms":("VLESS probe duration","ms"), "openai_ms":("OpenAI probe duration","ms")}
NODE = re.compile(r"node_[a-f0-9]{20}")
TAG = re.compile(r"vpn[0-9]{2,3}")


def messages(node,tag):
    if not NODE.fullmatch(node) or not TAG.fullmatch(tag):
        raise ValueError("invalid identity")
    topic=f"keenetic/vpn-monitor/v1/{node}/dynamic_history"
    for metric,(label,unit) in METRICS.items():
        uid=f"keenetic6059_dynamic_{node}_{metric}"
        payload={"name":f"{tag} {label}", "unique_id":uid,
                 "default_entity_id":f"sensor.keenetic_dynamic_{node}_{metric}",
                 "state_topic":topic,"value_template":"{{ value_json."+metric+" }}",
                 "expire_after":1800,
                 "json_attributes_topic":topic,
                 "json_attributes_template":
                     '{{ {"node_id": value_json.node_id, "tag": value_json.tag, "metric": "'+metric+'"} | to_json }}'}
        if unit:
            payload["unit_of_measurement"]=unit
        yield f"homeassistant/sensor/{uid}/config",payload


def state_payload(row):
    node,tag=row[:2]
    if not NODE.fullmatch(node) or not TAG.fullmatch(tag):
        raise ValueError("invalid identity")
    return {"node_id":node,"tag":tag,"vless":row[4],"openai":row[9],
            "vless_ms":row[6],"openai_ms":row[11],
            "vless_checked_at":row[5],"openai_checked_at":row[10]}


def publish_history(rows,*,publisher=publish_once,password_reader=load_password):
    password=password_reader("/opt/etc/vpn-monitor/mqtt-password")
    kw=dict(host="192.168.0.169",port=1883,username="keenetic_monitor",
            password=password,client_id="keenetic-vpn-dynamic-history")
    for row in rows:
        node,tag=row[:2]
        for topic,payload in messages(node,tag):
            publisher(**kw,topic=topic,payload=payload,retain=True)
        publisher(**kw,topic=f"keenetic/vpn-monitor/v1/{node}/dynamic_history",
                  payload=state_payload(row),retain=False)
