#!/usr/bin/env python3

import os
import signal
import subprocess
import time
from pathlib import Path

def identity(pid):
    proc = Path('/proc') / str(pid)

    raw = (proc / 'cmdline').read_bytes()
    args = [x.decode() for x in raw.split(b'\0') if x]

    stat = (proc / 'stat').read_text()
    tail = stat[stat.rfind(')') + 2:].split()
    start_ticks = int(tail[19])

    return args, start_ticks

p = subprocess.Popen(['/opt/bin/sleep', '60'])

try:
    pid = p.pid
    args, ticks = identity(pid)

    print('TEST_PID:', pid)
    print('IDENTITY_CAPTURED: YES')

    if args != ['/opt/bin/sleep', '60']:
        raise RuntimeError('Unexpected test process')

    args2, ticks2 = identity(pid)

    if (args, ticks) != (args2, ticks2):
        raise RuntimeError('Process identity changed')

    print('IDENTITY_VERIFIED: YES')

    # Only the child process created by this test.
    p.terminate()
    p.wait(timeout=5)

    print('TEST_PROCESS_STOPPED: YES')
    print('EXIT_CODE:', p.returncode)
    print('MAIN_XRAY_TOUCHED: NO')

finally:
    if p.poll() is None:
        p.kill()
        p.wait()
