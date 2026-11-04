"""OpenAI-specific MQTT discovery. Never confuse generic HTTP egress with API reachability.

Requires verified isolated check implementation before any live publication.
"""
import re
from monitoring.mqtt_lan_publisher import publish_once

_NODE = re.compile(r"^node_[0-9a-f]{20}$")
_TAG = re.compile(r"^vpn[0-9]{2,3}$")

FIELDS = {
    "status": ("OpenAI reachability", "{{ value_json.status }}", None),
    "checked_at": ("OpenAI checked at", "{{ value_json.checked_at }}", None),
    "test_duration_ms": ("OpenAI full test duration", "{{ value_json.test_duration_ms }}", "ms"),
}

def messages(node_id, tag):
    if not _NODE.fullmatch(node_id) or not _TAG.fullmatch(tag):
        raise ValueError("invalid VPN node")
    topic = f"keenetic/vpn-monitor/v1/{node_id}/openai_http"
    for metric, (label, template, unit) in FIELDS.items():
        uid = f"keenetic6059_{node_id}_openai_{metric}"
        config = {
            "name": f"{tag} {label}",
            "unique_id": uid,
            "state_topic": topic,
            "value_template": template,
            "expire_after": 1800,
            "qos": 1,
            "device": {
                "identifiers": [f"keenetic6059_{node_id}"],
                "name": f"Keenetic VPN {tag}",
                "manufacturer": "Keenetic",
                "model": "VLESS isolated OpenAI probe (not live user traffic)",
            },
        }
        if unit is not None:
            config["unit_of_measurement"] = unit
        yield f"homeassistant/sensor/{uid}/config", config

def publish_for_inventory(*, entries, host, username, password):
    total = 0
    for entry in entries:
        for topic, payload in messages(entry["node_id"], entry["tag"]):
            publish_once(host=host, port=1883, username=username,
                password=password, topic=topic, payload=payload,
                retain=True, client_id="keenetic-vpn-openai-discovery")
            total += 1
    return total
