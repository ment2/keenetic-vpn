"""Home Assistant MQTT discovery for per-interface traffic; discovery retained, states not retained."""
from monitoring.mqtt_lan_publisher import publish_once
from monitoring.traffic_one_shot import DEFAULT_INTERFACES

METRICS = {
    "rx_total_bytes": ("Received total", "B", "data_size", "total_increasing", "{{ value_json.rx_total_bytes }}"),
    "tx_total_bytes": ("Sent total", "B", "data_size", "total_increasing", "{{ value_json.tx_total_bytes }}"),
    "rx_bits_per_sec": ("Receive rate", "bit/s", "data_rate", "measurement", "{{ value_json.interval.rx_bits_per_sec if value_json.interval.status == 'ok' else 'None' }}"),
    "tx_bits_per_sec": ("Send rate", "bit/s", "data_rate", "measurement", "{{ value_json.interval.tx_bits_per_sec if value_json.interval.status == 'ok' else 'None' }}"),
}

def discovery_messages(interface):
    if interface not in DEFAULT_INTERFACES:
        raise ValueError("interface not allowed")
    state = f"keenetic/vpn-monitor/v1/traffic/{interface}"
    for field, (name, unit, devclass, stateclass, template) in METRICS.items():
        identifier = f"keenetic6059_{interface}_{field}"
        yield (
            f"homeassistant/sensor/{identifier}/config",
            {
                "name": f"{interface} {name}",
                "unique_id": identifier,
                "state_topic": state,
                "value_template": template,
                "unit_of_measurement": unit,
                "device_class": devclass,
                "state_class": stateclass,
                "qos": 1,
                "expire_after": 240,
                "device": {
                    "identifiers": ["keenetic6059_vpn_monitor"],
                    "name": "Keenetic VPN Monitoring",
                    "manufacturer": "Keenetic",
                    "model": "Interface counters (not VPN-only)"
                }
            }
        )

def publish_discovery(*, host, username, password, interfaces=DEFAULT_INTERFACES):
    count = 0
    for interface in interfaces:
        for topic, configuration in discovery_messages(interface):
            # Retained configuration survives an HA MQTT integration restart.
            publish_once(
                host=host, port=1883, username=username, password=password,
                topic=topic, payload=configuration, retain=True,
                client_id="keenetic-vpn-discovery"
            )
            count += 1
    return count
