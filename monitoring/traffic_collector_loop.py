"""Single-instance, stoppable traffic sampler. Does not install cron/services.

Run only locally on router with --publish after explicit consent.
All secret access stays inside the local process; no password in logs.
"""
import argparse
import fcntl
import os
import signal
import sys
import time
from pathlib import Path

from monitoring.traffic_one_shot import DEFAULT_INTERFACES, collect_once

def run_loop(*, interval_seconds=60, state_dir='/opt/var/lib/vpn-monitor/traffic',
             lock_file='/opt/var/lib/vpn-monitor/collector.lock',
             publish=False, max_cycles=0, interfaces=DEFAULT_INTERFACES):
    if not 30 <= interval_seconds <= 3600:
        raise ValueError('interval must be 30..3600 seconds')
    if max_cycles < 0:
        raise ValueError('max_cycles must not be negative')
    lock_path = Path(lock_file)
    lock_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(lock_path.parent, 0o700)
    with os.fdopen(os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600), 'r+') as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError('collector already running') from exc
        should_stop = [False]
        def request_stop(signum, frame):
            should_stop[0] = True
        prior_term = signal.signal(signal.SIGTERM, request_stop)
        prior_int = signal.signal(signal.SIGINT, request_stop)
        try:
            completed = 0
            while not should_stop[0]:
                start = time.monotonic()
                try:
                    results = collect_once(interfaces, state_dir, publish=publish)
                    print('CYCLE_OK', completed + 1, results, flush=True)
                except Exception as exc:
                    # Never print exception text (could contain credentials or remote data).
                    print('CYCLE_FAILED', completed + 1, type(exc).__name__, flush=True)
                completed += 1
                if max_cycles and completed >= max_cycles:
                    break
                deadline = start + interval_seconds
                while not should_stop[0] and time.monotonic() < deadline:
                    time.sleep(min(1, max(0, deadline - time.monotonic())))
        finally:
            signal.signal(signal.SIGTERM, prior_term)
            signal.signal(signal.SIGINT, prior_int)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--interval', type=int, default=60)
    parser.add_argument('--max-cycles', type=int, default=0, help='0 runs until terminated')
    parser.add_argument('--publish', action='store_true')
    parser.add_argument('--state-dir', default='/opt/var/lib/vpn-monitor/traffic')
    parser.add_argument('--lock-file', default='/opt/var/lib/vpn-monitor/collector.lock')
    args = parser.parse_args()
    run_loop(interval_seconds=args.interval, state_dir=args.state_dir,
             lock_file=args.lock_file, publish=args.publish, max_cycles=args.max_cycles)

if __name__ == '__main__':
    main()
