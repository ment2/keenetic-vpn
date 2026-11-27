"""RC2: independent Internet, OpenAI, exit-IP and geolocation probes.

No production config writes or service control. All four requests go through
one owned temporary loopback SOCKS listener. A positive HTTP witness is not
a general kernel no-leak proof or an authenticated OpenAI API test.
"""
import ipaddress
import json
import os
import re
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from monitoring.isolated_pair_probe import (
    XRAY, CURL, STARTUP_S, config_for, live_owner, stop_child, CleanupError)

HTTP_S = 8
NODE_BUDGET_S = 55
URLS = {
    "internet": "https://www.gstatic.com/generate_204",
    "openai": "https://api.openai.com/v1/models",
    "exit_ip": "https://api.ipify.org/?format=json",
    "geo": "https://ipwho.is/",
}


def ip_value(value):
    try:
        if not isinstance(value, str):
            return None
        return str(ipaddress.ip_address(value))
    except ValueError:
        return None


def city_value(value):
    if not isinstance(value,str):
        return None
    value=value.strip()
    if not 1<=len(value)<=64 or not all(c.isalnum() or c in " -.'’" for c in value):
        return None
    return value


def request(port, kind):
    body = kind in ("exit_ip","geo")
    env={k:v for k,v in os.environ.items()
         if k.lower() not in ("http_proxy","https_proxy","all_proxy","no_proxy")}
    args=[CURL,"-q","--silent","--show-error","--noproxy","",
          "--proxy","socks5h://127.0.0.1:%d"%port,
          "--connect-timeout","4","--max-time",str(HTTP_S)]
    if body:
        args += ["--fail","--max-filesize","8192"]
    else:
        args += ["--output","/dev/null","--write-out","%{http_code}"]
    return subprocess.run(args+[URLS[kind]],stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL,env=env,timeout=HTTP_S+2)


def classify(kind, result):
    if result is None:
        return {"status":"unknown"}
    if result.returncode:
        return {"status":"timeout" if result.returncode==28 else "network_error"}
    if kind in ("internet","openai"):
        expected=b"204" if kind=="internet" else b"401"
        return {"status":"ok" if result.stdout.strip()==expected else "http_error"}
    if len(result.stdout)>8192:
        return {"status":"invalid_response"}
    try:
        obj=json.loads(result.stdout)
        ip=ip_value(obj.get("ip"))
        if not ip:
            return {"status":"invalid_response"}
        if kind=="exit_ip":
            return {"status":"ok","ip":ip}
        if obj.get("success") is not True:
            return {"status":"geo_unavailable"}
        c=obj.get("country_code")
        country=c if isinstance(c,str) and re.fullmatch("[A-Z]{2}",c) else None
        city=city_value(obj.get("city"))
        if not country and not city:
            return {"status":"geo_unavailable","ip":ip}
        return {"status":"ok","ip":ip,"country":country,"city":city}
    except (ValueError,TypeError,AttributeError):
        return {"status":"invalid_response"}


def observe(proc,port,kind):
    start=time.monotonic()
    result=None
    verified=False
    timed_out=False
    if live_owner(proc,port):
        try:
            result=request(port,kind)
        except subprocess.TimeoutExpired:
            timed_out=True
        except OSError:
            pass
        verified=live_owner(proc,port)
    obs=classify(kind,result if verified else None)
    if timed_out and verified:
        obs={"status":"timeout"}
    obs.update(checked_at=int(time.time()),duration_ms=round((time.monotonic()-start)*1000),
               route_verified=verified and obs["status"]=="ok")
    return obs


def probe_node(outbound):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1",0))
        port=sock.getsockname()[1]
    result={}
    with tempfile.TemporaryDirectory(prefix="vpn-monitor-rc2-") as tmp:
        path=Path(tmp)/"probe.json"
        with os.fdopen(os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),"w") as f:
            json.dump(config_for(outbound,port),f)
        proc=subprocess.Popen([XRAY,"run","-config",str(path)],
                              stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            end=time.monotonic()+STARTUP_S
            while time.monotonic()<end and not live_owner(proc,port):
                if proc.poll() is not None:
                    break
                time.sleep(0.1)
            for kind in URLS:
                result[kind]=observe(proc,port,kind)
        finally:
            stop_child(proc)
    return result


def collect(config, entries, *, deadline, probe=probe_node):
    out={o["tag"]:o for o in config["outbounds"] if o.get("protocol")=="vless"}
    result={}
    for e in entries:
        if deadline-time.monotonic()<NODE_BUDGET_S:
            break
        try:
            result[e["node_id"]]=probe(out[e["tag"]])
        except CleanupError:
            raise
        except Exception:
            result[e["node_id"]]={}
    return result
