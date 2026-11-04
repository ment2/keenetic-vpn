"""Reuse the installed isolated OpenAI probe without touching production Xray.

The verified /opt/bin/xray_openai_probe.py exposes check(outbound) and returns
'reachable' only for HTTP 401 from https://api.openai.com/v1/models
through its temporary, loopback-only Xray SOCKS listener.
"""
import importlib.util
import time
from datetime import datetime, timezone
from monitoring.vpn_inventory import inventory
from monitoring.openai_health_contract import normalize_openai_result


def load_probe(path="/opt/bin/xray_openai_probe.py"):
    spec = importlib.util.spec_from_file_location("installed_openai_probe", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("probe script unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    probe = getattr(module, "check", None)
    if not callable(probe):
        raise RuntimeError("missing isolated OpenAI check")
    return probe


def probe_one(config, tag, probe):
    outbounds = [
        o for o in config.get("outbounds", [])
        if o.get("tag") == tag and o.get("protocol") == "vless"
    ]
    if len(outbounds) != 1:
        raise ValueError("missing/duplicate VLESS outbound")
    node = next(item for item in inventory(config) if item["tag"] == tag)
    started = time.monotonic()
    # Only explicit HTTP 401 from isolated SOCKS5-to-OpenAI demonstrates
    # that the OpenAI route actually worked; failures have no positive witness.
    try:
        raw = probe(outbounds[0])
    except Exception:
        raw = "unknown"
    duration_ms = min(120000, max(0, round((time.monotonic()-started)*1000)))
    return normalize_openai_result(tag, node["node_id"], raw,
        route_verified=(raw == "reachable"), duration_ms=duration_ms,
        checked_at=datetime.now(timezone.utc).isoformat())
