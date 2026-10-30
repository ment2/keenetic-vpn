#!/usr/bin/env python3

import base64
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, '/opt/bin')

from setup_xray import create_outbound
from xray_server_check import probe

ROOT = Path('/opt/etc/xray')
URLFILE = ROOT / 'subscription.url'

# Предварительный список по результатам сверки.
# Перед рабочим внедрением потребуется актуализация
# по официальному источнику OpenAI.
SUPPORTED = {'DE', 'US', 'FR'}

def load_subscription():
    if not URLFILE.is_file():
        raise RuntimeError('subscription file missing')

    if URLFILE.stat().st_mode & 0o077:
        raise RuntimeError('subscription permissions unsafe')

    url = URLFILE.read_text().strip()

    if not url.startswith('https://'):
        raise RuntimeError('HTTPS subscription required')

    r = subprocess.run(
        [
            '/opt/bin/curl',
            '--fail',
            '--silent',
            '--location',
            '--connect-timeout', '10',
            '--max-time', '60',
            url
        ],
        capture_output=True,
        timeout=65
    )

    if r.returncode:
        raise RuntimeError(
            'subscription download failed: ' + str(r.returncode)
        )

    body = r.stdout.strip()

    if len(body) < 10 or len(body) > 1024 * 1024:
        raise RuntimeError('invalid subscription size')

    if b'vless://' in body:
        decoded = body.decode('utf-8-sig')
    else:
        decoded = base64.b64decode(
            b''.join(body.split()),
            validate=True
        ).decode('utf-8-sig')

    lines = [
        s.strip()
        for s in decoded.splitlines()
        if s.strip().startswith('vless://')
    ]

    if not lines:
        raise RuntimeError('no VLESS servers')

    return lines


def main():
    lines = load_subscription()

    report = {
        'total': len(lines),
        'allowed': [],
        'excluded': [],
        'unverified': []
    }

    for i, line in enumerate(lines, 1):
        tag = 'vpn%02d' % i

        try:
            outbound, _ = create_outbound(line, i)
            result = probe(outbound)

            country = result.get('country_code')
            ip = result.get('ip')

            item = {
                'tag': tag,
                'country': country,
                'ip': ip
            }

            if result.get('status') != 'ok':
                item['reason'] = result.get('status')
                report['unverified'].append(item)
                state = 'UNVERIFIED'

            elif country in SUPPORTED:
                report['allowed'].append(item)
                state = 'ALLOWED'

            else:
                report['excluded'].append(item)
                state = 'EXCLUDED'

            print(
                '%s %s country=%s ip=%s' %
                (tag, state, country or '-', ip or '-'),
                flush=True
            )

        except Exception as exc:
            report['unverified'].append({
                'tag': tag,
                'reason': type(exc).__name__
            })

            print(
                '%s UNVERIFIED error=%s' %
                (tag, type(exc).__name__),
                flush=True
            )

    print()
    print('=== SUMMARY ===')
    print('TOTAL:', report['total'])
    print('ALLOWED:', len(report['allowed']))
    print('EXCLUDED:', len(report['excluded']))
    print('UNVERIFIED:', len(report['unverified']))
    print('CONFIG CHANGED: NO')
    print('XRAY RESTARTED: NO')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(
            'ERROR:', type(exc).__name__,
            file=sys.stderr
        )
        sys.exit(1)
