#!/usr/bin/env python3
"""Offline candidate: require owned HTTP204 and HTTP401, independent of geography.
Never applies a candidate or manages production processes, routes or firewall.
Based on exact live builder blob e9a5b68e; probe helpers derived from RC2.
"""

import base64
import copy
import json
import hashlib
import ipaddress
import re
import socket
import time
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, '/opt/bin')

from setup_xray import create_outbound

ROOT = Path('/opt/etc/xray')
CONFIG = ROOT / 'config.json'
URLFILE = ROOT / 'subscription.url'
XRAY = '/opt/sbin/xray'

# The complete qualification generation must fit the updater window.
CURL = "/opt/bin/curl"
STARTUP_S = 5
CYCLE_BUDGET_S = 720
VALIDATION_RESERVE_S = 40
MAX_PROBE_AGE_S = 120
MAX_NODES = 24

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


class CleanupError(RuntimeError):
    pass


def stop_child(proc):
    try:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CleanupError("isolated child cleanup failed") from exc


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
        return {"status":"ok","http_code":int(expected)} if result.stdout.strip()==expected else {"status":"http_error"}
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
    if not valid_vless(outbound, outbound.get("tag")):
        raise ValueError("unexpected outbound")
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




def valid_vless(outbound, tag):
    if not isinstance(outbound, dict) or not isinstance(tag, str):
        return False
    if not re.fullmatch(r"vpn[0-9]{2,3}", tag):
        return False
    if outbound.get("tag") != tag or outbound.get("protocol") != "vless":
        return False
    # Reject explicit outbound chaining: the tested route must be this node.
    if outbound.get("proxySettings") is not None:
        return False
    stream = outbound.get("streamSettings", {})
    if not isinstance(stream, dict):
        return False
    sockopt = stream.get("sockopt", {})
    return isinstance(sockopt, dict) and not sockopt.get("dialerProxy")


def verified(obs, code, now):
    if not isinstance(obs, dict):
        return False
    stamp = obs.get("checked_at")
    actual = obs.get("http_code")
    return (obs.get("status") == "ok" and obs.get("route_verified") is True
            and type(actual) is int and actual == code
            and type(stamp) is int and 0 <= now-stamp <= MAX_PROBE_AGE_S)


def qualify(observations, now):
    if not isinstance(observations, dict):
        return False
    return (verified(observations.get("internet"), 204, now)
            and verified(observations.get("openai"), 401, now))


def observation_status(observations, kind):
    obs = observations.get(kind, {}) if isinstance(observations, dict) else {}
    status = obs.get("status") if isinstance(obs, dict) else None
    return status if isinstance(status, str) and status in (
        "ok","unknown","timeout","network_error","http_error",
        "invalid_response","geo_unavailable") else "unknown"


def select_pool(lines, *, deadline, converter=None, probe=None, clock=time.time,
                monotonic=time.monotonic):
    converter = create_outbound if converter is None else converter
    probe = probe_node if probe is None else probe
    if not 1 <= len(lines) <= MAX_NODES:
        raise RuntimeError("unsupported subscription size")
    allowed, unverified = [], []
    for i, line in enumerate(lines, 1):
        if deadline-monotonic() < NODE_BUDGET_S+VALIDATION_RESERVE_S:
            # Never silently install a partially traversed subscription.
            raise RuntimeError("qualification budget exhausted")
        tag = "vpn%02d" % i
        try:
            outbound, _ = converter(line, i)
            if not valid_vless(outbound, tag):
                raise ValueError("unexpected outbound")
            result = probe(copy.deepcopy(outbound))
            good = qualify(result, clock())
            if good:
                allowed.append(outbound)
            else:
                unverified.append(tag)
            print("%s %s internet=%s openai=%s exit_ip=%s geo=%s" %
                  (tag, "ALLOWED" if good else "UNVERIFIED",
                   *(observation_status(result,k) for k in ("internet","openai","exit_ip","geo"))),
                  flush=True)
        except CleanupError:
            # Unknown child lifetime is a global safety failure, not a bad node.
            raise
        except Exception as exc:
            unverified.append(tag)
            print("%s UNVERIFIED error=%s" % (tag, type(exc).__name__), flush=True)
    if deadline-monotonic() < VALIDATION_RESERVE_S:
        raise RuntimeError("validation budget exhausted")
    return allowed, unverified


def write_candidate(path, data):
    # Output is a new wrapper-owned staging file. Never overwrite another file.
    fd = os.open(path, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
    except BaseException:
        # Wrapper exits on nonzero; its private temp directory is removed.
        raise



def subscription():
    if not URLFILE.is_file():
        raise RuntimeError('subscription file missing')

    if URLFILE.stat().st_mode & 0o077:
        raise RuntimeError('unsafe subscription permissions')

    url = URLFILE.read_text().strip()

    if not url.startswith('https://'):
        raise RuntimeError('HTTPS subscription required')

    with tempfile.TemporaryDirectory() as td:
        target = Path(td) / 'subscription'

        r = subprocess.run([
            '/opt/bin/curl',
            '--fail',
            '--silent',
            '--location',
            '--connect-timeout', '10',
            '--max-time', '60',
            '--output', str(target),
            url
        ], stdout=subprocess.DEVNULL,
           stderr=subprocess.DEVNULL,
           timeout=65)

        if r.returncode:
            raise RuntimeError('subscription curl failed')

        body = target.read_bytes().strip()

    if not 10 <= len(body) <= 1024 * 1024:
        raise RuntimeError('invalid subscription size')

    if b'vless://' in body:
        decoded = body.decode('utf-8-sig')
    else:
        decoded = base64.b64decode(
            b''.join(body.split()),
            validate=True
        ).decode('utf-8-sig')

    lines = [
        line.strip()
        for line in decoded.splitlines()
        if line.strip().startswith('vless://')
    ]

    if not lines:
        raise RuntimeError('no VLESS entries')

    return lines


def main():
    output = None
    if len(sys.argv) == 3 and sys.argv[1] == '--output':
        output = Path(sys.argv[2])
    elif len(sys.argv) != 1:
        raise RuntimeError('invalid arguments')

    deadline = time.monotonic()+CYCLE_BUDGET_S
    current = json.loads(CONFIG.read_text(encoding='utf-8'))
    lines = subscription()
    print('SUBSCRIPTION SERVERS:', len(lines), flush=True)
    allowed, unverified = select_pool(lines, deadline=deadline)
    excluded = []

    print('\n=== FILTER SUMMARY ===')
    print('ALLOWED:', len(allowed))
    print('EXCLUDED:', len(excluded))
    print('UNVERIFIED:', len(unverified))

    if not allowed:
        print('VALIDATION: SKIPPED (no allowed servers)')
        print('CONFIG CHANGED: NO')
        raise RuntimeError('empty candidate pool')

    candidate = copy.deepcopy(current)

    # Keep non-VLESS outbounds from the existing config.
    others = [
        x for x in candidate.get('outbounds', [])
        if x.get('protocol') != 'vless'
    ]

    # Fail closed: no direct/freedom outbound.
    others = [
        x for x in others
        if x.get('protocol') not in ('freedom', 'blackhole')
    ]

    # Non-VLESS outbounds may not match the VPN selector or reserved tags.
    tags = [x.get("tag") for x in allowed+others]
    if (any(not isinstance(t,str) or not t for t in tags)
            or len(set(tags)) != len(tags)
            or any(t.startswith("vpn") or t=="blocked" for t in
                   [x.get("tag","") for x in others])):
        raise RuntimeError("ambiguous outbound tags")
    candidate['outbounds'] = allowed + others + [{
        'tag': 'blocked',
        'protocol': 'blackhole'
    }]

    routing = candidate.setdefault('routing', {})
    first_tag = allowed[0]['tag']

    routing['balancers'] = [{
        'tag': 'auto',
        'selector': ['vpn'],
        'strategy': {'type': 'leastPing'},
        'fallbackTag': first_tag
    }]

    # One VPN pool for both existing inbounds.
    routing['rules'] = [{
        'type': 'field',
        'inboundTag': ['local-socks', 'tproxy-in'],
        'balancerTag': 'auto'
    }, {
        'type': 'field',
        'network': 'tcp,udp',
        'outboundTag': 'blocked'
    }]

    candidate['observatory'] = {
        'subjectSelector': ['vpn'],
        'probeUrl': 'https://www.google.com/generate_204',
        'probeInterval': '60s',
        'enableConcurrency': True
    }

    # Ensure the selected fallback belongs to the pool.
    assert first_tag in {x['tag'] for x in allowed}

    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / 'candidate.json'
        path.write_text(
            json.dumps(candidate, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        os.chmod(path, 0o600)

        test = subprocess.run(
            [XRAY, 'run', '-test', '-config', str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30
        )

        print('\n=== CANDIDATE VALIDATION ===')
        print('XRAY TEST:', 'PASS' if test.returncode == 0 else 'FAIL')
        print('POOL:', ', '.join(x['tag'] for x in allowed))
        print('FALLBACK:', first_tag)
        print('CONFIG CHANGED: NO')
        print('XRAY RESTARTED: NO')
        print('CRON CHANGED: NO')

        if test.returncode:
            raise RuntimeError('candidate Xray validation failed')

        if time.monotonic() >= deadline:
            raise RuntimeError("qualification cycle expired")
        if output is not None:
            write_candidate(output, path.read_bytes())


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(
            'ERROR:', type(exc).__name__,
            file=sys.stderr
        )
        sys.exit(1)
