"""Home Assistant MQTT discovery for isolated VPN probe results.

These are per-node health checks, not live Xray-observatory RTT or traffic usage.
"""
import re
from monitoring.mqtt_lan_publisher import publish_once

ID = re.compile(r"^node_[0-9a-f]{20}$")
FIELDS = {
    "status": ("VPN status", "{{ value_json.status }}", None),
    "egress_ip": ("VPN egress IP", "{{ value_json.egress_ip if value_json.egress_ip else 'unknown' }}", None),
    "country_code": ("VPN country", "{{ value_json.country_code if value_json.country_code else 'unknown' }}", None),
    "test_duration_ms": ("Full probe duration", "{{ value_json.test_duration_ms }}", "ms"),
}

def messages(node_id, tag):
    if not ID.fullmatch(node_id) or not re.fullmatch(r"vpn[0-9]{2,3}",tag):
        raise ValueError("unsafe node identity")
    state_topic=f"keenetic/vpn-monitor/v1/{node_id}/health"
    for metric,(label,template,unit) in FIELDS.items():
        unique_id=f"keenetic6059_{node_id}_{metric}"
        payload={
            "name":f"{tag} {label}",
            "unique_id":unique_id,
            "state_topic":state_topic,
            "value_template":template,
            "expire_after":1800,
            "qos":1,
            "device":{
                "identifiers":[f"keenetic6059_{node_id}"],
                "name":f"Keenetic VPN {tag}",
                "manufacturer":"Keenetic",
                "model":"VLESS isolated probe (not live traffic)"
            }
        }
        if unit:payload["unit_of_measurement"]=unit
        yield f"homeassistant/sensor/{unique_id}/config",payload

def publish_for_inventory(*, entries, host, username, password):
    sent=0
    for entry in entries:
        for topic,payload in messages(entry["node_id"],entry["tag"]):
            publish_once(host=host,port=1883,username=username,password=password,
                topic=topic,payload=payload,retain=True,
                client_id="keenetic-vpn-health-discovery")
            sent+=1
    return sent
