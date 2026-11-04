"""Safe, strict normalization of per-node OpenAI reachability evidence.

Pure/offline contract only. No router access, no Xray process, no MQTT secrets.
Unlike generic VLESS HTTP egress, OpenAI success requires an explicit
'reachable' result from the isolated per-outbound OpenAI probe.
"""
from datetime import datetime, timezone
import re

_ALLOWED = {"reachable", "network_error", "http_error", "timeout", "unreachable", "unknown"}
_TAG = re.compile(r"^vpn[0-9]{2,3}$")
_NODE = re.compile(r"^node_[0-9a-f]{20}$")


def normalize_openai_result(tag, node_id, raw, *, route_verified, duration_ms, checked_at=None):
    if not _TAG.fullmatch(tag) or not _NODE.fullmatch(node_id):
        raise ValueError("invalid node identity")
    if type(route_verified) is not bool:
        raise ValueError("route provenance must be explicit")
    if isinstance(duration_ms, bool) or not isinstance(duration_ms, int) or not 0 <= duration_ms <= 120000:
        raise ValueError("invalid duration")
    # Fail closed: only exact contract value 'reachable' constitutes positive evidence.
    # Other existing results are sanitized categories, not free text exceptions.
    status = raw if isinstance(raw, str) else (raw.get("status") if isinstance(raw, dict) else None)
    if status not in _ALLOWED:
        status = "unknown"
    if status == "reachable" and not route_verified:
        status = "unknown"
    timestamp = checked_at or datetime.now(timezone.utc).isoformat()
    if not isinstance(timestamp, str) or len(timestamp) > 45:
        raise ValueError("invalid timestamp")
    parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must carry offset")
    return {
        "schema": 1,
        "node_id": node_id,
        "tag": tag,
        "status": status,
        "route_verified": route_verified,
        "checked_at": timestamp,
        "test_duration_ms": duration_ms,
        "test_kind": "isolated_xray_openai_http",
        "latency_is_rtt": False,
    }
