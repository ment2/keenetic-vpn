"""One-shot interface counter snapshot and opt-in MQTT publish.

No cron/service installation, no mutation of Xray, routing or firewall.
Credentials are accessed only by the script when run locally on Keenetic.
"""
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from monitoring.mqtt_lan_publisher import publish_once, load_password
from monitoring.traffic_counters import read_snapshot, interval, Sample

DEFAULT_INTERFACES = ('apclii0', 'br0', 'br1')

def event_from_sample(sample: Sample, previous: Sample | None, timestamp: str):
    if previous is None:
        value = {"status": "baseline", "reason": "first_sample"}
    else:
        value = interval(previous, sample)
    return {
        "schema": 1,
        "timestamp": timestamp,
        "interface": sample.iface,
        "rx_total_bytes": sample.rx_bytes,
        "tx_total_bytes": sample.tx_bytes,
        "interval": value,
        "vpn_specific": False,
    }

def snapshot_dict(sample):
    return {
        "iface": sample.iface,
        "boot_id": sample.boot_id,
        "monotonic_ns": sample.monotonic_ns,
        "rx_bytes": sample.rx_bytes,
        "tx_bytes": sample.tx_bytes,
    }

def previous_sample(path, iface):
    try:
        data = json.loads(path.read_text())
        if data.get('iface') != iface:
            return None
        return Sample(**data)
    except (FileNotFoundError, ValueError, TypeError, KeyError, OSError):
        return None

def save_snapshot_atomic(path, sample):
    """Write state with restrictive permissions and atomic replace; never store credentials."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    temporary = path.with_name(path.name + '.new')
    with os.fdopen(os.open(temporary, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600), 'w') as out:
        json.dump(snapshot_dict(sample), out, separators=(',', ':'))
        out.flush()
        os.fsync(out.fileno())
    os.replace(temporary, path)

def collect_once(interfaces, state_dir, publish=False, broker='192.168.0.169', username='keenetic_monitor', secret_file='/opt/etc/vpn-monitor/mqtt-password'):
    stamp = datetime.now(timezone.utc).isoformat()
    results = []
    for iface in interfaces:
        sample = read_snapshot(iface)
        path = Path(state_dir) / (iface + '.json')
        old = previous_sample(path, iface)
        event = event_from_sample(sample, old, stamp)
        save_snapshot_atomic(path, sample)
        if publish:
            password = load_password(secret_file)
            publish_once(host=broker, port=1883, username=username, password=password,
                         topic=f'keenetic/vpn-monitor/v1/traffic/{iface}', payload=event)
        results.append((iface, event['interval']['status']))
    return results

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--interface', action='append', choices=DEFAULT_INTERFACES)
    parser.add_argument('--state-dir', default='/opt/var/lib/vpn-monitor/traffic')
    parser.add_argument('--publish', action='store_true', help='opt-in authenticated LAN MQTT publish')
    args = parser.parse_args()
    for iface, status in collect_once(args.interface or DEFAULT_INTERFACES, args.state_dir, args.publish):
        print(f'INTERFACE={iface} STATUS={status} MQTT={"PUBACK_OK" if args.publish else "NOT_SENT"}')

if __name__ == '__main__':
    main()
