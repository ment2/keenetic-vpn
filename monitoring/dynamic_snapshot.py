"""Offline candidate: full-subscription monitoring, never modifies live VPN config.
The full input MUST be an independently verified unfiltered Xray-format snapshot.
Do not point --full at config.json, config.pending.json or an old backup.
"""
import argparse
import fcntl
import ipaddress
import json
import os
import re
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from monitoring.vpn_inventory import inventory

TOPIC = "keenetic/vpn-monitor/v1/dynamic_rc2"
DISCOVERY = "homeassistant/sensor/keenetic6059_dynamic_rc2/config"
ACTIVE = "/opt/etc/xray/config.json"
PENDING = "/opt/etc/xray/config.pending.json"
CACHE = "/opt/var/lib/vpn-monitor/dynamic-probes-rc2.json"
MAX_PROBE_AGE = 1800
MAX_INPUT_AGE = 1800
MAX_PAYLOAD = 32768
MAX_NODES = 24


def read_config(path, now=None):
    p = Path(path)
    with p.open() as f:
        mtime = os.fstat(f.fileno()).st_mtime
        data = json.load(f)
    if now is not None and not 0 <= now - mtime <= MAX_INPUT_AGE:
        raise ValueError("stale subscription snapshot")
    entries = inventory(data)
    if len({e["tag"] for e in entries}) != len(entries):
        raise ValueError("duplicate tag")
    if len(entries) > MAX_NODES:
        raise ValueError("inventory capacity exceeded")
    return data, entries


def pool_ids(path, optional=False):
    try:
        return {e["node_id"] for e in read_config(path)[1]}
    except FileNotFoundError:
        if optional:
            return set()
    except (ValueError, KeyError, TypeError, OSError, AttributeError):
        pass
    return None


def measure(event, node_id, kind, now):
    if not isinstance(event, dict) or event.get("node_id") != node_id:
        return ["missing", None, None, None, None]
    expected = {"health": "isolated_xray_http204", "geo": "isolated_xray_http_egress", "openai": "isolated_xray_openai_http"}[kind]
    if event.get("test_kind") != expected:
        return ["missing", None, None, None, None]
    try:
        dt = datetime.fromisoformat(event["checked_at"].replace("Z", "+00:00"))
        if dt.tzinfo is None:
            raise ValueError()
        stamp = int(dt.timestamp())
        if not 0 <= now - stamp <= MAX_PROBE_AGE:
            return ["stale", stamp, None, None, None]
    except (ValueError, KeyError, TypeError, AttributeError, OverflowError):
        return ["missing", None, None, None, None]
    success = "reachable" if kind == "openai" else "ok"
    status = event.get("status")
    allowed = {"ok", "failed", "unknown"} if kind != "openai" else {"reachable", "network_error", "http_error", "timeout", "unreachable", "unknown"}
    if not isinstance(status, str) or status not in allowed or (status == success and event.get("route_verified") is not True):
        status = "unknown"
    ms = event.get("test_duration_ms")
    if type(ms) is not int or not 0 <= ms <= 120000:
        ms = None
    ip = country = None
    if kind == "geo" and status == success:
        try:
            ip = str(ipaddress.ip_address(event.get("egress_ip")))
        except ValueError:
            status = "unknown"
        c = event.get("country_code")
        if ip and isinstance(c, str) and re.fullmatch("[A-Z]{2}", c):
            country = c
    return [status, stamp, ms, ip, country]


def endpoint_labels(config):
    labels = {}
    for outbound in config.get("outbounds", []):
        if outbound.get("protocol") != "vless":
            continue
        server = outbound["settings"]["vnext"][0]
        address = server["address"]
        port = int(server["port"])
        # Only hostname/IP and port; never URI, credentials or parameters.
        try:
            address = str(ipaddress.ip_address(address))
        except ValueError:
            if not isinstance(address, str) or not re.fullmatch(r"[A-Za-z0-9.-]{1,253}", address):
                address = None
        if address and 1 <= port <= 65535:
            labels[outbound["tag"]] = [address, port]
    return labels


def geo_details(obs, node, now):
    from monitoring.isolated_pair_probe import clean_city
    current = measure(obs.get("geo"), node, "geo", now)
    prior = obs.get("last_geo")
    if current[0] == "ok":
        event = obs["geo"]
        return [*current, clean_city(event.get("city"))]
    if isinstance(prior, dict):
        try:
            stamp = datetime.fromisoformat(prior["checked_at"].replace("Z","+00:00")).timestamp()
            # Last known data are never treated as fresh after a failed attempt.
            if 0 <= now-stamp <= 86400:
                old = measure(prior, node, "geo", stamp)
                if old[0] == "ok":
                    return ["stale", old[1], old[2], old[3], old[4], clean_city(prior.get("city"))]
        except (ValueError,TypeError,KeyError,AttributeError,OverflowError):
            pass
    return [*current, None]


def retain_geo(previous, current, entries, now=None):
    now = time.time() if now is None else now
    result = {}
    for entry in entries:
        node = entry["node_id"]
        old = previous.get(node, {}) if isinstance(previous, dict) else {}
        new = dict(current.get(node, {}))
        if not isinstance(old, dict):
            old = {}
        candidate = new.get("geo")
        if measure(candidate, node, "geo", now)[0] != "ok":
            candidate = old.get("last_geo")
        if isinstance(candidate, dict) and candidate.get("node_id") == node:
            try:
                dt = datetime.fromisoformat(candidate["checked_at"].replace("Z","+00:00"))
                stamp = dt.timestamp()
                if dt.tzinfo is not None and 0 <= now-stamp <= 86400 and measure(candidate,node,"geo",stamp)[0] == "ok":
                    new["last_geo"] = candidate
            except (ValueError,TypeError,KeyError,AttributeError,OverflowError):
                pass
        result[node] = new
    return result


def snapshot(entries, active, pending, observations, now, endpoints=None):
    rows = []
    for e in entries:
        node = e["node_id"]
        obs = observations.get(node, {})
        if not isinstance(obs, dict):
            obs = {}
        h = measure(obs.get("health"), node, "health", now)
        o = measure(obs.get("openai"), node, "openai", now)
        g = geo_details(obs, node, now)
        endpoint = (endpoints or {}).get(e["tag"], [None,None])
        # Preserve RC1 column offsets for history; append RC2 fields.
        rows.append([node, e["tag"], None if active is None else node in active,
                     None if pending is None else node in pending, *h[:3], g[3], g[4], *o[:3], *endpoint, g[0], g[1], g[5], g[2]])
    known = {e["node_id"] for e in entries}
    result = {"schema": 2, "checked_at": int(now), "count": len(rows),
              "inventory_status": "ok", "rows": rows,
              "active_unmatched": None if active is None else len(active-known),
              "pending_unmatched": None if pending is None else len(pending-known)}
    if len(json.dumps(result, separators=(",", ":"), ensure_ascii=True).encode()) > MAX_PAYLOAD:
        raise ValueError("snapshot payload exceeds MQTT limit")
    return result


def atomic_cache(path, observations):
    p = Path(path)
    fd, temp = tempfile.mkstemp(prefix=".dynamic-", dir=str(p.parent))
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(observations, f, separators=(",", ":"))
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, p)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def run_probes(config, entries, health_probe, openai_probe, deadline=None):
    observations = {}
    for e in entries:
        if deadline is not None and time.monotonic() >= deadline:
            break
        obs = observations[e["node_id"]] = {}
        for kind, probe in (("health", health_probe), ("openai", openai_probe)):
            if deadline is not None and time.monotonic() >= deadline:
                return observations
            try:
                obs[kind] = probe(config, e["tag"])
            except Exception:
                # A failed/missing probe must never inherit an old success.
                obs[kind] = None
    return observations


def discovery():
    return {"name": "Keenetic dynamic VPN inventory", "unique_id": "keenetic6059_dynamic_rc2",
            "default_entity_id": "sensor.keenetic_dynamic_vpn_rc2", "state_topic": TOPIC,
            "value_template": "{{ value_json.inventory_status }}",
            "json_attributes_topic": TOPIC, "expire_after": 150}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["probe", "publish"])
    parser.add_argument("--full", required=True)
    parser.add_argument("--cache", default=CACHE)
    parser.add_argument("--active", default=ACTIVE)
    parser.add_argument("--pending", default=PENDING)
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    full = Path(args.full).resolve()
    if full in {Path(args.active).resolve(), Path(args.pending).resolve(), Path(ACTIVE).resolve(), Path(PENDING).resolve()}:
        raise SystemExit("unfiltered subscription required")
    if args.mode == "probe":
        from monitoring.isolated_pair_probe import collect
        with os.fdopen(os.open(args.cache + ".lock", os.O_CREAT | os.O_RDWR, 0o600), "r+") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            config, entries = read_config(full, time.time())
            result = collect(config, entries, deadline=time.monotonic()+480)
            try:
                previous = json.loads(Path(args.cache).read_text())
            except (OSError, ValueError):
                previous = {}
            completed = len(result)
            result = retain_geo(previous, result, entries)
            atomic_cache(args.cache, result)
            if args.publish:
                from monitoring.dynamic_history import publish_history
                rows = snapshot(entries, None, None, result, time.time(), endpoint_labels(config))["rows"]
                publish_history(rows, deadline=time.monotonic()+120)
        print("PROBE_CYCLE", completed, "of", len(entries))
        return
    now = time.time()
    try:
        config, entries = read_config(full, now)
        if not entries:
            raise ValueError("empty subscription")
        try:
            with open(args.cache) as f:
                obs = json.load(f)
            if not isinstance(obs, dict):
                obs = {}
        except (OSError, ValueError):
            obs = {}
        result = snapshot(entries, pool_ids(args.active), pool_ids(args.pending, optional=True), obs, now, endpoint_labels(config))
    except (ValueError, OSError, KeyError, TypeError, AttributeError):
        result = {"schema": 2, "checked_at": int(now), "inventory_status": "unavailable", "count": 0, "rows": []}
    if args.publish:
        from monitoring.mqtt_lan_publisher import load_password, publish_once
        kw = dict(host="192.168.0.169", port=1883, username="keenetic_monitor",
                  password=load_password("/opt/etc/vpn-monitor/mqtt-password"),
                  client_id="keenetic-vpn-dynamic")
        publish_once(**kw, topic=DISCOVERY, payload=discovery(), retain=True)
        publish_once(**kw, topic=TOPIC, payload=result)
    print("SNAPSHOT", result["inventory_status"], result["count"])


if __name__ == "__main__":
    main()
