"""Pure change-decision gate for the OpenAI-qualified Xray candidate.

Critical: equality with PENDING must never be treated as equality with LIVE.
No router writes, starts, kills or restarts. The apply runner must separately
establish exclusive ownership and safely replace the live process.
"""
import hashlib
import json
from pathlib import Path

def _canonical(raw):
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Xray config must be an object")
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

def decide(live_bytes, candidate_bytes, pending_bytes=None):
    live = _canonical(live_bytes)
    candidate = _canonical(candidate_bytes)
    candidate_obj = json.loads(candidate)
    tags=[o["tag"] for o in candidate_obj.get("outbounds",[]) if o.get("protocol")=="vless"]
    if not tags:
        return {"decision":"reject","reason":"no_vless","live_changes":False}
    for b in candidate_obj.get("routing",{}).get("balancers",[]):
        fb=b.get("fallbackTag")
        if fb and fb not in tags:
            return {"decision":"reject","reason":"fallback_outside_pool","live_changes":False}
    # A candidate matching staged pending still differs from live until applied.
    if candidate == live:
        return {"decision":"unchanged","reason":"live_equal","live_changes":False,
                "live_sha256":hashlib.sha256(live_bytes).hexdigest(),
                "candidate_sha256":hashlib.sha256(candidate_bytes).hexdigest()}
    return {"decision":"apply_required","reason":"live_differs","live_changes":True,
            "pending_equal": (pending_bytes is not None and _canonical(pending_bytes)==candidate),
            "live_sha256":hashlib.sha256(live_bytes).hexdigest(),
            "candidate_sha256":hashlib.sha256(candidate_bytes).hexdigest()}

def inspect_paths(live="/opt/etc/xray/config.json",candidate="/opt/etc/xray/config.pending.json"):
    l=Path(live).read_bytes(); c=Path(candidate).read_bytes()
    return decide(l,c,c)

if __name__=="__main__":
    status=inspect_paths()
    print(json.dumps(status,sort_keys=True))
