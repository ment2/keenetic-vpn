#!/usr/bin/env python3

from pathlib import Path

EXPECTED = [
    '/opt/sbin/xray',
    'run',
    '-config',
    '/opt/etc/xray/config.json'
]

def identity(pid):
    proc = Path('/proc') / str(pid)

    raw = (proc / 'cmdline').read_bytes()
    args = [
        x.decode('utf-8')
        for x in raw.split(b'\0')
        if x
    ]

    if args != EXPECTED:
        raise RuntimeError('PROCESS_COMMAND_MISMATCH')

    stat = (proc / 'stat').read_text()
    # The comm field may contain spaces or parentheses.
    tail = stat[stat.rfind(')') + 2:].split()
    start_ticks = int(tail[19])

    return pid, start_ticks

def find_main():
    matches = []

    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue

        try:
            matches.append(identity(int(proc.name)))
        except (OSError, UnicodeError, ValueError, RuntimeError):
            continue

    return matches

first = find_main()

if len(first) != 1:
    raise SystemExit('UNSAFE: expected exactly one main Xray')

second = identity(first[0][0])

if first[0] != second:
    raise SystemExit('UNSAFE: process identity changed')

print('IDENTITY: VERIFIED')
print('MAIN_PID:', second[0])
print('START_TICKS:', second[1])
print('SIGNAL_SENT: NO')
print('XRAY_RESTARTED: NO')
