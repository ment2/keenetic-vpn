"""Read-only Xray VLESS outbound inventory.

Never print user UUID, server host, REALITY public key, or full config.
Stable IDs exclude mutable vpnNN tags and client UUIDs.
"""
import json
import re
from pathlib import Path
from monitoring.telemetry import stable_node_id

TAG = re.compile(r"^vpn[0-9]{2,3}$")

def inventory(config):
    result = []
    seen_ids = set()
    for outbound in config.get("outbounds", []):
        if outbound.get("protocol") != "vless":
            continue
        tag = outbound.get("tag", "")
        if not TAG.fullmatch(tag):
            raise ValueError("unexpected VLESS outbound tag")
        servers = outbound.get("settings", {}).get("vnext", [])
        if len(servers) != 1:
            raise ValueError("VLESS outbound needs exactly one endpoint")
        server = servers[0]
        stream = outbound.get("streamSettings", {})
        network = stream.get("network", "tcp")
        security = stream.get("security", "none")
        reality = stream.get("realitySettings") or {}
        tls = stream.get("tlsSettings") or {}
        # A server's actual network identity, not its subscription array position.
        # UUID is explicitly excluded because it is client/account-specific.
        node = stable_node_id(
            address=server["address"],
            port=int(server["port"]),
            network=network,
            transport=security,
            public_key=reality.get("publicKey", ""),
            flow=(server.get("users") or [{}])[0].get("flow", ""),
        )
        if node in seen_ids:
            raise ValueError("duplicate VLESS endpoint")
        seen_ids.add(node)
        result.append({"tag":tag, "node_id":node, "kind":"vless", "vpn_specific":True})
    return sorted(result, key=lambda x: x["tag"])

def sanitized_inventory(path="/opt/etc/xray/config.json"):
    config = json.loads(Path(path).read_text())
    return inventory(config)

def main():
    for item in sanitized_inventory():
        print(item["tag"], item["node_id"], item["kind"])

if __name__=="__main__":
    main()
