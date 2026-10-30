"""Offline v30 endpoint identity primitives. NOT connected to live Xray.

Fingerprint the full outbound configuration excluding the positional Xray tag.
HMAC protects sensitive VLESS IDs/credentials against offline guessing from logs.
The key must be a durable secret outside GitHub, not generated on each refresh.
"""
import hashlib
import hmac
import json


def canonical_outbound(outbound: dict) -> bytes:
    if not isinstance(outbound, dict) or outbound.get("protocol") != "vless":
        raise ValueError("only VLESS endpoints supported")
    if not outbound.get("settings") or not isinstance(outbound["settings"], dict):
        raise ValueError("VLESS settings required")
    normalized = {k: v for k, v in outbound.items() if k != "tag"}
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def identity(outbound: dict, hmac_key: bytes) -> str:
    if not isinstance(hmac_key, bytes) or len(hmac_key) < 32:
        raise ValueError("durable HMAC key must have at least 32 bytes")
    return hmac.new(hmac_key, canonical_outbound(outbound), hashlib.sha256).hexdigest()


def stable_tag(outbound: dict, hmac_key: bytes) -> str:
    return "vpn-" + identity(outbound, hmac_key)[:24]


def tag_map(outbounds: list[dict], hmac_key: bytes) -> dict[str, str]:
    result = {}
    for outbound in outbounds:
        digest = identity(outbound, hmac_key)
        if digest in result:
            raise ValueError("duplicate VPN endpoint in subscription")
        tag = "vpn-" + digest[:24]
        if tag in result.values():
            raise ValueError("stable tag collision")
        result[digest] = tag
    return result
