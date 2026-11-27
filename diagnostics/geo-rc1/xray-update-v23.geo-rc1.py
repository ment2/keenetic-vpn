#!/usr/bin/env python3
"""Read-only Xray subscription candidate builder."""

import base64
import copy
import json
import ipaddress
import socket
import time
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, '/opt/bin')

from setup_xray import create_outbound
from xray_openai_probe import check as check_openai

ROOT = Path('/opt/etc/xray')
CONFIG = ROOT / 'config.json'
URLFILE = ROOT / 'subscription.url'
XRAY = '/opt/sbin/xray'

# Geo gate RC1: ISO 3166-1 alpha-2, deny RU/BY. No lookup by endpoint country.
BLOCKED_COUNTRIES = frozenset(("RU", "BY"))
COUNTRY_CODES = frozenset(("AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG UM US UY UZ VA VC VE VG VI VN VU WF WS YE YT ZA ZM ZW").split())
CURL = '/opt/bin/curl'


def public_ip(value):
    if not isinstance(value, str):
        return None
    try:
        ip = ipaddress.ip_address(value)
        if ip.is_global and not ip.is_multicast and not ip.is_reserved and not ip.is_unspecified:
            return ip
    except ValueError:
        pass
    return None


def geo_decision(result):
    if not isinstance(result, dict) or result.get('status') != 'ok':
        return 'UNVERIFIED'
    ip = public_ip(result.get('ip'))
    country = result.get('country_code')
    if ip is None or not isinstance(country, str) or country.upper() not in COUNTRY_CODES:
        return 'UNVERIFIED'
    country = country.upper()
    if country in BLOCKED_COUNTRIES:
        return 'EXCLUDED_' + country
    if public_ip(result.get('witness_ip')) != ip:
        return 'UNVERIFIED'
    return 'ELIGIBLE'


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

def probe(outbound):
    port = free_port()
    config = {
        "log": {"loglevel": "warning"},
        "inbounds": [{
            "tag": "probe-in",
            "listen": "127.0.0.1",
            "port": port,
            "protocol": "socks",
            "settings": {"auth": "noauth", "udp": False}
        }],
        "outbounds": [dict(outbound, tag="probe-out")],
        "routing": {
            "rules": [{
                "type": "field",
                "inboundTag": ["probe-in"],
                "outboundTag": "probe-out"
            }]
        }
    }

    with tempfile.TemporaryDirectory(
        prefix="xray-probe-"
    ) as td:
        path = Path(td) / "config.json"
        path.write_text(json.dumps(config))
        os.chmod(path, 0o600)

        try:
            test = subprocess.run(
                [XRAY, "run", "-test", "-config", str(path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10
            )
            if test.returncode:
                return {"status": "invalid_config"}

            proc = subprocess.Popen(
                [XRAY, "run", "-config", str(path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except (OSError, subprocess.TimeoutExpired):
            return {"status": "startup_error"}

        try:
            for _ in range(30):
                if proc.poll() is not None:
                    return {"status": "xray_exited"}
                with socket.socket() as s:
                    if s.connect_ex(("127.0.0.1", port)) == 0:
                        break
                time.sleep(0.2)
            else:
                return {"status": "startup_timeout"}

            env = {
                k: v for k, v in os.environ.items()
                if k.lower() not in (
                    "http_proxy", "https_proxy",
                    "all_proxy", "no_proxy"
                )
            }

            cmd = [
                CURL, "-q",
                "--silent", "--show-error", "--fail",
                "--noproxy", "",
                "--proxy", f"socks5h://127.0.0.1:{port}",
                "--connect-timeout", "7",
                "--max-time", "20",
                "https://ipwho.is/"
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=23,
                env=env
            )

            if result.returncode:
                return {"status": "network_error"}

            if len(result.stdout) > 8192:
                return {"status": "invalid_response"}

            data = json.loads(result.stdout)

            if (
                data.get("success") is not True
                or not isinstance(data.get("ip"), str)
                or not isinstance(data.get("country_code"), str)
                or len(data["country_code"]) != 2
            ):
                return {"status": "geo_unavailable"}

            # Independent IP witness through the SAME isolated SOCKS listener.
            # Never infer the exit country from a VLESS endpoint or its hostname.
            geo_ip = public_ip(data["ip"])
            if geo_ip is None:
                return {"status": "invalid_egress_ip"}
            country = data["country_code"].upper()
            if country not in COUNTRY_CODES:
                return {"status": "geo_unavailable"}
            if country in BLOCKED_COUNTRIES:
                return {"status": "ok", "ip": str(geo_ip),
                        "country_code": country}
            witness = subprocess.run([
                CURL, "-q", "--silent", "--show-error", "--fail",
                "--noproxy", "", "--proxy", f"socks5h://127.0.0.1:{port}",
                "--connect-timeout", "4", "--max-time", "8",
                "https://api.ipify.org"
            ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
               timeout=11, env=env)
            if witness.returncode or len(witness.stdout) > 256:
                return {"status": "egress_unverified"}
            witness_ip = public_ip(witness.stdout.decode("ascii").strip())
            if witness_ip is None or witness_ip != geo_ip:
                return {"status": "egress_mismatch"}
            return {"status": "ok", "ip": str(geo_ip),
                    "country_code": country, "witness_ip": str(witness_ip)}

        except (OSError, ValueError,
                subprocess.TimeoutExpired):
            return {"status": "probe_error"}

        finally:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()


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

    current = json.loads(CONFIG.read_text(encoding='utf-8'))
    lines = subscription()

    allowed = []
    excluded = []
    unverified = []

    print('SUBSCRIPTION SERVERS:', len(lines), flush=True)

    for i, line in enumerate(lines, 1):
        tag = 'vpn%02d' % i

        try:
            outbound, _ = create_outbound(line, i)
            result = probe(outbound)

            country = result.get('country_code')
            ip = result.get('ip')

            state = geo_decision(result)
            if state.startswith('EXCLUDED_'):
                excluded.append(tag)
            elif state != 'ELIGIBLE':
                unverified.append(tag)
                state = 'UNVERIFIED'
            else:
                api_status = check_openai(outbound)
                if api_status == 'reachable':
                    allowed.append(outbound)
                    state = 'ALLOWED'
                else:
                    unverified.append(tag)
                    state = 'API_' + api_status.upper()

            print(
                '%s %-10s country=%s ip=%s' %
                (tag, state, country or '-', ip or '-'),
                flush=True
            )

        except Exception as exc:
            unverified.append(tag)
            print(
                '%s UNVERIFIED error=%s' %
                (tag, type(exc).__name__),
                flush=True
            )

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

        if output is not None:
            if output.exists() or output.is_symlink():
                raise RuntimeError('output already exists')
            output.write_bytes(path.read_bytes())
            os.chmod(output, 0o600)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(
            'ERROR:', type(exc).__name__,
            file=sys.stderr
        )
        sys.exit(1)
