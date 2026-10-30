#!/usr/bin/env python3

import os
import sys
from pathlib import Path

CONFIG = '/opt/etc/xray/config.json'
EXPECTED = [
    '/opt/sbin/xray',
    'run',
    '-config',
    CONFIG
]

def find_main():
    found = []

    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue

        try:
            args = [
                x.decode('utf-8')
                for x in (proc / 'cmdline').read_bytes().split(b'\0')
                if x
            ]
        except (OSError, UnicodeError):
            continue

        if args == EXPECTED:
            found.append(int(proc.name))

    return found

def status():
    pids = find_main()

    if len(pids) == 0:
        print('STATUS: NOT_RUNNING')
        return 1

    if len(pids) > 1:
        print('STATUS: MULTIPLE_MAIN_PROCESSES')
        print('COUNT:', len(pids))
        return 2

    pid = pids[0]

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        print('STATUS: PROCESS_DISAPPEARED')
        return 1
    except PermissionError:
        print('STATUS: PERMISSION_DENIED')
        return 2

    print('STATUS: OK')
    print('MAIN_PID:', pid)
    print('CONFIG:', CONFIG)
    print('CONTROL_ACTION: NONE')
    return 0

if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] != 'status':
        print('Only read-only status is supported')
        sys.exit(2)

    sys.exit(status())
