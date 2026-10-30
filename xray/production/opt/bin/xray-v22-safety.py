#!/usr/bin/env python3
"""Read-only routing safety validation for Xray."""

import json
import subprocess
import tempfile
from pathlib import Path

CONFIG = Path('/opt/etc/xray/config.json')
XRAY = '/opt/sbin/xray'

def main():
    cfg = json.loads(CONFIG.read_text())

    print('=== CURRENT CONFIG ===')

    inbounds = {
        x.get('tag')
        for x in cfg.get('inbounds', [])
    }

    print('INBOUNDS:', ', '.join(sorted(inbounds)))

    routing = cfg.get('routing', {})

    for rule in routing.get('rules', []):
        print(
            'RULE:',
            rule.get('inboundTag'),
            '->',
            rule.get('balancerTag') or rule.get('outboundTag')
        )

    print('\n=== BUILD SAFE CANDIDATE ===')

    # Copy configuration without modifying the original.
    candidate = json.loads(json.dumps(cfg))

    # Remove direct/freedom outbound.
    candidate['outbounds'] = [
        x for x in candidate.get('outbounds', [])
        if x.get('protocol') != 'freedom'
    ]

    # Add explicit blackhole outbound.
    candidate['outbounds'].append({
        'tag': 'blocked',
        'protocol': 'blackhole'
    })

    # Ensure a VPN outbound is first.
    if not candidate['outbounds']:
        raise RuntimeError('No outbounds')

    if candidate['outbounds'][0].get('protocol') != 'vless':
        raise RuntimeError('First outbound is not VPN')

    routing = candidate.setdefault('routing', {})

    routing['rules'] = [{
        'type': 'field',
        'inboundTag': ['local-socks', 'tproxy-in'],
        'balancerTag': 'auto'
    }]

    # Reject unexpected inbounds.
    expected = {'local-socks', 'tproxy-in'}

    if inbounds != expected:
        raise RuntimeError('Unexpected inbound configuration')

    # Verify balancer fallback.
    balancers = routing.get('balancers', [])
    auto = next(
        (x for x in balancers if x.get('tag') == 'auto'),
        None
    )

    if not auto:
        raise RuntimeError('Missing auto balancer')

    fallback = auto.get('fallbackTag')

    vpn_tags = {
        x['tag']
        for x in candidate['outbounds']
        if x.get('protocol') == 'vless'
    }

    if fallback not in vpn_tags:
        raise RuntimeError('Unsafe fallback')

    # Explicitly block traffic not matching the VPN rule.
    routing['rules'].append({
        'type': 'field',
        'network': 'tcp,udp',
        'outboundTag': 'blocked'
    })

    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / 'candidate.json'
        path.write_text(json.dumps(candidate))
        path.chmod(0o600)

        result = subprocess.run(
            [XRAY, 'run', '-test', '-config', str(path)],
            capture_output=True,
            timeout=30
        )

        print('XRAY TEST:',
              'PASS' if result.returncode == 0 else 'FAIL')

        print('DIRECT OUTBOUNDS:',
              sum(
                  x.get('protocol') == 'freedom'
                  for x in candidate['outbounds']
              ))

        print('BLACKHOLE: ENABLED')
        print('VPN FALLBACK:', fallback)

        print('CONFIG CHANGED: NO')
        print('XRAY RESTARTED: NO')

        if result.returncode:
            raise RuntimeError('Xray validation failed')

if __name__ == '__main__':
    main()
