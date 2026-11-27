"""Candidate isolated monitor probes. No service/firewall/route management.

Only a private, temporary Xray configuration and an owned child are used.
Both HTTP observations independently require a live listener owned by that
child before and after the request. This is not a kernel no-leak acceptance test.
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
from monitoring.vpn_node_probe import normalize_result
from monitoring.openai_health_contract import normalize_openai_result
from monitoring.vpn_inventory import inventory

XRAY = "/opt/sbin/xray"
CURL = "/opt/bin/curl"
STARTUP_S = 5
HTTP_S = 12
PAIR_BUDGET_S = 45


def owned_listener(pid, port, proc_root="/proc"):
    """Match IPv4 loopback LISTEN inode with the child's actual FD table."""
    root = Path(proc_root)
    try:
        # /proc/net/tcp encodes IPv4 in host byte order; target is MIPS32LE.
        endpoint = "0100007F:%04X" % port
        with (root / "net/tcp").open() as f:
            next(f, None)
            inodes = {p[9] for line in f for p in [line.split()]
                      if len(p) > 9 and p[1].upper() == endpoint and p[3] == "0A"}
        if len(inodes) != 1:
            return False
        inode = next(iter(inodes))
        for fd in (root / str(pid) / "fd").iterdir():
            try:
                if os.readlink(fd) == "socket:[%s]" % inode:
                    return True
            except OSError:
                continue
    except (OSError, ValueError):
        return False
    return False


def live_owner(proc, port):
    return proc.poll() is None and owned_listener(proc.pid, port) and proc.poll() is None


def config_for(outbound, port):
    return {"log":{"loglevel":"warning"},
            "inbounds":[{"tag":"probe-in","listen":"127.0.0.1","port":port,
                         "protocol":"socks","settings":{"auth":"noauth","udp":False}}],
            "outbounds":[{"protocol":"blackhole","tag":"blocked"},dict(outbound,tag="probe-out")],
            "routing":{"domainStrategy":"AsIs","rules":[
                {"type":"field","inboundTag":["probe-in"],"outboundTag":"probe-out"}]}}


def http_request(port, url, *, body=False):
    # -q MUST be the first curl option. No redirects, no config, no credentials,
    # no proxy env, no direct fallback.
    env = {k:v for k,v in os.environ.items()
           if k.lower() not in ("http_proxy","https_proxy","all_proxy","no_proxy")}
    cmd = [CURL,"-q","--silent","--show-error","--noproxy","",
           "--proxy","socks5h://127.0.0.1:%d"%port,
           "--connect-timeout","5","--max-time",str(HTTP_S)]
    if body:
        cmd += ["--fail","--max-filesize","8192"]
    else:
        cmd += ["--output","/dev/null","--write-out","%{http_code}"]
    return subprocess.run(cmd+[url], stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL, env=env, timeout=HTTP_S+2)


def geo_result(result):
    if result.returncode or len(result.stdout)>8192:
        return {"status":"failed"}
    try:
        d=json.loads(result.stdout)
        ip=str(ipaddress.ip_address(d["ip"]))
        country=d["country_code"]
        if d.get("success") is True and isinstance(country,str) and re.fullmatch("[A-Z]{2}",country):
            return {"status":"ok","ip":ip,"country_code":country}
    except (ValueError,TypeError,KeyError,AttributeError):
        pass
    return {"status":"failed"}


def openai_result(result):
    if result.returncode:
        return "network_error"
    code=result.stdout.strip()
    return "reachable" if code==b"401" else "http_error"


def query_owned(proc, port, url, body=False):
    if not live_owner(proc,port):
        return None
    try:
        result=http_request(port,url,body=body)
    except (OSError,subprocess.TimeoutExpired):
        return None
    return result if live_owner(proc,port) else None


def stop_child(proc):
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2)


def probe_pair(config, tag):
    node=next(e["node_id"] for e in inventory(config) if e["tag"]==tag)
    outbound=next(o for o in config["outbounds"] if o.get("tag")==tag and o.get("protocol")=="vless")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1",0))
        port=sock.getsockname()[1]
    result={}
    with tempfile.TemporaryDirectory(prefix="vpn-monitor-probe-") as tmp:
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
            start=time.monotonic()
            h=query_owned(proc,port,"https://ipwho.is/",body=True)
            result["health"]=normalize_result(tag,node,geo_result(h) if h is not None else {"status":"unknown"},time.monotonic()-start)
            if h is None:
                result["health"]["status"]="unknown"
            start=time.monotonic()
            o=query_owned(proc,port,"https://api.openai.com/v1/models")
            status=openai_result(o) if o is not None else "unknown"
            result["openai"]=normalize_openai_result(tag,node,status,
                route_verified=(o is not None),duration_ms=round((time.monotonic()-start)*1000))
        finally:
            stop_child(proc)
    return result


def collect(config, entries, *, deadline, probe=probe_pair):
    results={}
    for e in entries:
        # Do not begin a pair if it cannot fit in the conservative budget.
        if deadline-time.monotonic()<PAIR_BUDGET_S:
            break
        try:
            results[e["node_id"]]=probe(config,e["tag"])
        except Exception:
            results[e["node_id"]]={}
    return results
