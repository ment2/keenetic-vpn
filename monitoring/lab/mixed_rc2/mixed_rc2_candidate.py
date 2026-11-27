"""Offline RC2 mixed-protocol candidate. No production I/O or publishing.
Private outbounds stay in memory; only rows() output may be published after acceptance.
"""
import base64
import hashlib
import ipaddress
import json
import re
from urllib.parse import parse_qsl, unquote, urlsplit

KINDS = ('internet', 'openai', 'exit_ip', 'geo')
FRESH = 1800
COUNTRIES = frozenset('AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG UM US UY UZ VA VC VE VG VI VN VU WF WS YE YT ZA ZM ZW'.split())

# Recognize security-sensitive aliases for classification only; do not silently
# translate or admit them until the provider's exact contract is reviewed.
TLS_ALIASES = frozenset('allowinsecure skipcertverify noverify insecure insecureskipverify tlsinsecure tlsskipverify skipverify skipverification disabletlsverify verify'.split())

REASONS = frozenset(('unsupported_option', 'ech_unverified', 'duplicate_option', 'tls_policy', 'invalid_uri'))

class Unsupported(ValueError):
    def __init__(self, message, reason='invalid_uri'):
        super().__init__(message)
        self.reason = reason if reason in REASONS else 'invalid_uri' 

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def host(value):
    if not isinstance(value, str) or not value:
        raise ValueError('invalid host')
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        value = value.rstrip('.').encode('idna').decode('ascii').lower()
        if len(value) > 253 or not all(re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', p) for p in value.split('.')):
            raise ValueError('invalid host') from None
        return value

def decode(body):
    if not isinstance(body, bytes) or not 1 <= len(body) <= 1048576:
        raise ValueError('invalid response size')
    b = body.strip()
    if b'://' not in b:
        b = base64.b64decode(b''.join(b.split()), validate=True)
    lines = [x.strip() for x in b.decode('utf-8-sig').splitlines() if x.strip()]
    if not 1 <= len(lines) <= 64:
        raise ValueError('invalid inventory size')
    return lines

def fm_legacy(raw, mask):
    """Translate only reviewed FinalMask shape to Xray 26.2.6. Never silently drop options."""
    def unique(pairs):
        obj = dict(pairs)
        if len(obj) != len(pairs):
            raise ValueError('duplicate JSON key')
        return obj
    if not isinstance(raw, str) or not 1 <= len(raw) <= 16384:
        raise Unsupported('invalid FinalMask size', 'unsupported_option')
    try:
        fm = json.loads(raw, object_pairs_hook=unique)
    except (ValueError, RecursionError):
        raise Unsupported('invalid FinalMask JSON', 'unsupported_option') from None
    if (not isinstance(fm, dict) or set(fm) - {'udp', 'quicParams'}
            or mask is None or fm.get('udp') != mask.get('udp')):
        raise Unsupported('unreviewed or inconsistent FinalMask', 'unsupported_option')
    quic = fm.get('quicParams', {})
    if not isinstance(quic, dict) or set(quic) - {'congestion', 'keepAlivePeriod', 'maxIdleTimeout'}:
        raise Unsupported('unreviewed QUIC options', 'unsupported_option')
    if 'congestion' in quic and quic['congestion'] != 'bbr':
        raise Unsupported('unreviewed congestion mode', 'unsupported_option')
    for key, lo, hi in (('keepAlivePeriod', 2, 60), ('maxIdleTimeout', 4, 120)):
        if key in quic and (type(quic[key]) is not int or not (quic[key] == 0 or lo <= quic[key] <= hi)):
            raise Unsupported('invalid QUIC timing', 'unsupported_option')
    return dict(quic)


def hy2(uri, tag):
    u = urlsplit(uri)
    h = host(u.hostname)
    try:
        port = 443 if u.port is None else u.port
    except ValueError:
        raise Unsupported('port hopping not accepted in candidate') from None
    if not 1 <= port <= 65535 or u.path not in ('', '/'):
        raise Unsupported('unsupported endpoint syntax')
    raw_auth = u.netloc.rsplit('@', 1)[0] if '@' in u.netloc else ''
    if re.search(r'%(?![0-9a-fA-F]{2})', raw_auth + u.query):
        raise Unsupported('invalid percent encoding')
    auth = unquote(raw_auth, errors='strict')
    pairs = parse_qsl(u.query, keep_blank_values=True, strict_parsing=True, max_num_fields=32, errors='strict')
    q = dict(pairs)
    if len(q) != len(pairs):
        raise Unsupported('duplicate URI options', 'duplicate_option')
    aliases = [k for k in q if k != 'insecure' and re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', k) and re.sub(r'[-_]', '', k.casefold()) in TLS_ALIASES]
    if aliases:
        raise Unsupported('unreviewed TLS verification option', 'tls_policy')
    if q.get('insecure', '0') != '0':
        raise Unsupported('insecure TLS not accepted', 'tls_policy')
    if set(q) - {'sni', 'insecure', 'obfs', 'obfs-password', 'ech', 'fm'}:
        raise Unsupported('unknown URI options', 'unsupported_option')
    if 'ech' in q:
        raise Unsupported('ECH mapping not verified', 'ech_unverified')
    if not auth or len(auth) > 4096 or any(ord(c) < 32 or ord(c) == 127 for c in auth):
        raise Unsupported('invalid auth')
    sni = host(q.get('sni') or h)
    stream = {'network': 'hysteria', 'security': 'tls', 'tlsSettings': {'serverName': sni, 'alpn': ['h3']}, 'hysteriaSettings': {'version': 2, 'auth': auth}}
    obfs = q.get('obfs', '')
    if obfs == 'salamander' and q.get('obfs-password'):
        stream['finalmask'] = {'udp': [{'type': 'salamander', 'settings': {'password': q['obfs-password']}}]}
    elif obfs or 'obfs-password' in q:
        raise Unsupported('unsupported obfuscation')
    if 'fm' in q:
        stream['hysteriaSettings'].update(fm_legacy(q['fm'], stream.get('finalmask')))
    return {'tag': tag, 'protocol': 'hysteria', 'settings': {'version': 2, 'address': h, 'port': port}, 'streamSettings': stream}

def generation(o):
    return digest({k: v for k, v in o.items() if k != 'tag'})

def build(body, vless_converter, vless_inventory):
    """Returns private records; do not log or publish. Keeps old VLESS tag ordering."""
    records, vl, hy = [], 0, 0
    for uri in decode(body):
        reason = None
        u = urlsplit(uri)
        scheme = u.scheme.lower()
        if scheme == 'vless':
            vl += 1
            tag = 'vpn%02d' % vl
            o, _ = vless_converter(uri, vl)
            if o.get('tag') != tag or o.get('protocol') != 'vless':
                raise ValueError('invalid VLESS conversion')
            entries = vless_inventory({'outbounds': [o]})
            if len(entries) != 1:
                raise ValueError('invalid VLESS identity')
            s = o['settings']['vnext'][0]
            h, p, node = host(s['address']), s['port'], entries[0]['node_id']
            protocol, status = 'vless', 'ready'
        elif scheme in ('hy2', 'hysteria2'):
            hy += 1
            tag = 'hy%02d' % hy
            protocol, status = 'hysteria2', 'ready'
            h = host(u.hostname)
            try:
                p = 443 if u.port is None else u.port
            except ValueError:
                p = None
            node = 'hy2_' + digest([protocol, h, p])[:20]
            try:
                o = hy2(uri, tag)
            except Unsupported as exc:
                o, status, reason = None, 'unsupported', exc.reason
            except ValueError:
                o, status, reason = None, 'unsupported', 'invalid_uri'
        else:
            raise ValueError('unrecognized subscription scheme')
        if any(r['id'] == node for r in records):
            raise ValueError('duplicate identity')
        if protocol == 'vless' and (type(p) is not int or not 1 <= p <= 65535):
            raise ValueError('invalid VLESS port')
        if protocol == 'hysteria2' and (type(p) is not int or not 1 <= p <= 65535):
            p = None
        records.append({'id': node, 'tag': tag, 'protocol': protocol, 'host': h, 'port': p, 'support': status, 'support_reason': reason, 'outbound': o, 'generation': generation(o) if o else None})
    return records

def observation(raw, kind, now):
    default = {'status': 'missing', 'at': None, 'ms': None}
    if not isinstance(raw, dict) or type(raw.get('checked_at')) is not int:
        return default
    at = raw['checked_at']
    if not 0 <= now - at <= FRESH:
        return {'status': 'stale', 'at': at, 'ms': None}
    ms = raw.get('duration_ms')
    status = raw.get('status')
    if not isinstance(status, str) or status not in ('ok', 'timeout', 'network_error', 'http_error', 'invalid_response', 'geo_unavailable', 'unknown') or (status == 'ok' and raw.get('route_verified') is not True):
        status = 'unknown'
    result = {'status': status, 'at': at, 'ms': ms if type(ms) is int and 0 <= ms <= 120000 else None}
    if status == 'ok' and kind in ('exit_ip', 'geo'):
        try:
            ip = ipaddress.ip_address(raw.get('ip'))
            if not ip.is_global or ip.is_multicast or ip.is_reserved:
                raise ValueError('nonpublic IP')
            result['ip'] = str(ip)
        except (ValueError, TypeError):
            result['status'] = 'invalid_response'
        if kind == 'geo':
            country = raw.get('country')
            if not isinstance(country, str) or country not in COUNTRIES:
                result['status'] = 'geo_unavailable'
            else:
                result['country'] = country
                city = raw.get('city')
                if isinstance(city, str) and 1 <= len(city.strip()) <= 64 and all(c.isalnum() or c in " -.'’" for c in city.strip()):
                    result['city'] = city.strip()
    return result

def rows(records, cache, active, now, pending=None):
    """Sanitized RC2-like rows; active is a read-only id -> generation mapping."""
    output = []
    for r in records:
        c = cache.get(r['id'], {})
        raw = c.get('observations', {}) if isinstance(c, dict) and c.get('generation') == r['generation'] and r['outbound'] else {}
        if not isinstance(raw, dict):
            raw = {}
        obs = {k: observation(raw.get(k), k, now) for k in KINDS}
        if r['support'] != 'ready':
            obs = {k: {'status': 'unsupported', 'at': None, 'ms': None} for k in KINDS}
        ip, geo = obs['exit_ip'], obs['geo']
        verified_geo = ip['status'] == geo['status'] == 'ok' and ip.get('ip') == geo.get('ip') and abs(ip['at'] - geo['at']) <= 55
        decision = 'UNVERIFIED'
        if verified_geo:
            country = geo['country']
            decision = 'EXCLUDED_' + country if country in ('RU', 'BY') else 'ALLOWED'
        elif ip['status'] == geo['status'] == 'ok':
            obs['geo'] = {'status': 'ip_mismatch' if ip.get('ip') != geo.get('ip') else 'unverified_time', 'at': geo['at'], 'ms': geo['ms']}
        positive = [v['at'] for v in obs.values() if v['status'] == 'ok']
        attempted = [v['at'] for v in obs.values() if v['at'] is not None and v['status'] != 'stale']
        member = None if active is None else r['id'] in active
        pending_member = None if pending is None else r['id'] in pending
        coherent = all(v['at'] is not None and v['status'] == 'ok' for v in obs.values()) and max(v['at'] for v in obs.values()) - min(v['at'] for v in obs.values()) <= 55
        safe_reason = r.get('support_reason')
        output.append(dict({k: r[k] for k in ('id', 'tag', 'protocol', 'host', 'port', 'support')}, active=member, pending=pending_member, pending_config_matches=(pending[r['id']] == r['generation'] if pending_member else None), active_config_matches=(active[r['id']] == r['generation'] if member else None), vpn={'status': 'ok' if positive else 'not_confirmed' if attempted else r['support'] if r['support'] != 'ready' else 'missing', 'at': max(positive or attempted, default=None)}, internet=obs['internet'], openai=obs['openai'], exit_ip=ip.get('ip') if ip['status'] == 'ok' else None, exit_ip_at=ip['at'] if ip['status'] == 'ok' else None, exit_ip_source='exit_ip' if ip['status'] == 'ok' else None, exit_ip_probe=ip, geo=obs['geo'], last_geo=None, geo_policy=decision, eligible=decision == 'ALLOWED' and coherent))
        if r['support'] != 'ready':
            output[-1]['support_reason'] = safe_reason if isinstance(safe_reason, str) and safe_reason in REASONS else 'invalid_uri'
    return output

def collect(records, probe, deadline, monotonic, cleanup_error):
    """Probe one private outbound at a time with the existing isolated RC2 probe.
    Caller supplies its CleanupError class; never swallow containment failure.
    """
    cache = {}
    for r in records:
        if not r['outbound']:
            continue
        if deadline - monotonic() < 55:
            break
        try:
            obs = probe(r['outbound'])
            if not isinstance(obs, dict):
                obs = {}
        except cleanup_error:
            raise
        except Exception:
            obs = {}
        cache[r['id']] = {'generation': r['generation'], 'observations': obs}
    return cache


def payload(records, cache, active, now, subscription_at, pending=None):
    if type(subscription_at) is not int or not 0 <= now - subscription_at <= FRESH:
        return {'schema': 2, 'inventory_status': 'unavailable', 'count': 0, 'rows': []}
    data = rows(records, cache, active, now, pending)
    ids = {r['id'] for r in data}
    counts = {p: sum(r['protocol'] == p for r in data) for p in ('vless', 'hysteria2')}
    complete = sum(all(r[k]['at'] is not None and r[k]['status'] != 'stale' for k in ('internet', 'openai', 'geo', 'exit_ip_probe')) for r in data)
    result = {'schema': 2, 'checked_at': now, 'subscription_at': subscription_at, 'inventory_status': 'ok', 'count': len(data), 'protocol_counts': counts, 'rows': data, 'probe_complete': complete, 'unsupported_count': sum(r['support'] != 'ready' for r in data), 'active_unmatched': None if active is None else len(set(active)-ids), 'pending_unmatched': None if pending is None else len(set(pending)-ids)}
    if len(json.dumps(result, separators=(',', ':'), ensure_ascii=True).encode()) > 32768:
        raise ValueError('RC2 payload capacity exceeded')
    return result
