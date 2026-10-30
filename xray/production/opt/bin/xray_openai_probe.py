#!/usr/bin/env python3
"""Test OpenAI API reachability through one isolated Xray outbound."""

import json
import os
import socket
import subprocess
import tempfile
import time
from pathlib import Path

XRAY = '/opt/sbin/xray'
CURL = '/opt/bin/curl'


def check(outbound):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]

    config = {
        'log': {'loglevel': 'warning'},
        'inbounds': [{
            'tag': 'probe-in',
            'listen': '127.0.0.1',
            'port': port,
            'protocol': 'socks',
            'settings': {'auth': 'noauth', 'udp': False}
        }],
        'outbounds': [
            dict(outbound, tag='probe-out'),
            {'tag': 'blocked', 'protocol': 'blackhole'}
        ],
        'routing': {
            'rules': [{
                'type': 'field',
                'inboundTag': ['probe-in'],
                'outboundTag': 'probe-out'
            }]
        }
    }

    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / 'config.json'
        path.write_text(json.dumps(config))
        os.chmod(path, 0o600)

        process = subprocess.Popen(
            [XRAY, 'run', '-config', str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        try:
            time.sleep(2)

            if process.poll() is not None:
                return 'xray_start_failed'

            result = subprocess.run([
                CURL,
                '--silent',
                '--show-error',
                '--noproxy', '',
                '--proxy', f'socks5h://127.0.0.1:{port}',
                '--connect-timeout', '10',
                '--max-time', '25',
                '--output', '/dev/null',
                '--write-out', '%{http_code}',
                'https://api.openai.com/v1/models'
            ], capture_output=True, text=True, timeout=30)

            if result.returncode == 0 and result.stdout.strip() == '401':
                return 'reachable'

            if result.returncode:
                return 'network_error'

            return 'http_' + result.stdout.strip()

        except subprocess.TimeoutExpired:
            return 'timeout'

        finally:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
