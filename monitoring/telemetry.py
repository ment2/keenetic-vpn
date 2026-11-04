"""Offline schema utilities for Keenetic VPN monitoring. No router I/O."""
import hashlib, ipaddress, json
from datetime import datetime

SCHEMA_VERSION = 1

def stable_node_id(*, address: str, port: int, network: str, transport: str, public_key: str = "", flow: str = "") -> str:
    """Stable across vpnNN ordering; never pass credentials or VLESS user UUIDs."""
    if not address or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("invalid endpoint")
    canonical = [address.rstrip(".").lower(), port, network.lower(), transport.lower(), public_key, flow]
    return "node_" + hashlib.sha256(json.dumps(canonical, ensure_ascii=True, separators=(",", ":")).encode()).hexdigest()[:20]

def validate_measurement(event: dict) -> dict:
    """Only allow sanitized telemetry after explicit VPN route verification."""
    if set(event) != {"node_id", "tag", "checked_at", "route_verified", "status", "rtt_ms", "egress_ip", "probe"}:
        raise ValueError("unknown/missing telemetry fields")
    if not isinstance(event["node_id"], str) or not event["node_id"].startswith("node_"):
        raise ValueError("invalid node ID")
    if not isinstance(event["route_verified"], bool):
        raise ValueError("route provenance required")
    if event["status"] not in ("ok", "failed", "unknown"):
        raise ValueError("invalid status")
    if event["status"] == "ok" and not event["route_verified"]:
        raise ValueError("cannot report success without route witness")
    if event["probe"] not in ("openai_http", "telegram_tcp", "egress_https"):
        raise ValueError("probe not allowed")
    if not isinstance(event["tag"], str) or len(event["tag"]) > 32:
        raise ValueError("invalid tag")
    dt = datetime.fromisoformat(event["checked_at"].replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timezone required")
    val = event["rtt_ms"]
    if val is not None and (isinstance(val, bool) or not isinstance(val, (int, float)) or not 0 <= val <= 120000):
        raise ValueError("invalid RTT")
    if event["egress_ip"] is not None:
        ipaddress.ip_address(event["egress_ip"])
    return {"schema": SCHEMA_VERSION, **event}

def mqtt_topic(event: dict) -> str:
    node_id = event["node_id"]
    if not node_id.startswith("node_") or not all(ch in "abcdef0123456789" for ch in node_id[5:]):
        raise ValueError("unsafe topic")
    return f"keenetic/vpn-monitor/v1/{node_id}/{event['probe']}"
