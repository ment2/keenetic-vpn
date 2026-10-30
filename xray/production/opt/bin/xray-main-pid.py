#!/usr/bin/env python3

from pathlib import Path

EXPECTED = [
    '/opt/sbin/xray',
    'run',
    '-config',
    '/opt/etc/xray/config.json'
]

found = []

for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():
        continue

    try:
        raw = (proc / 'cmdline').read_bytes()
        args = [
            x.decode('utf-8')
            for x in raw.split(b'\0')
            if x
        ]
    except (OSError, UnicodeError):
        continue

    if args == EXPECTED:
        found.append(int(proc.name))

if len(found) == 1:
    print('MAIN_XRAY_PID:', found[0])
    print('STATUS: OK')
elif not found:
    print('MAIN_XRAY_PID: NONE')
    print('STATUS: NOT_RUNNING')
else:
    print('MAIN_XRAY_PID: MULTIPLE')
    print('STATUS: UNSAFE')
    raise SystemExit(1)
