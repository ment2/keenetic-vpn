#!/opt/bin/python3
"""Operator-approved single-job recovery. NEVER run automatically."""
import getpass
import json
import subprocess
import sys

BASE = 'https://keenetic-control-bridge.wlad124650.workers.dev'
JOB = 'da2d6c64-d60d-4cc5-bd67-66b8b3a16908'
admin = getpass.getpass('CONTROL_ADMIN_TOKEN: ')
policy = getpass.getpass('CONTROL_POLICY_TOKEN: ')

def request(method, path, payload=None):
    args = ['curl', '-q', '-sS', '--socks5-hostname', '127.0.0.1:10808',
            '--connect-timeout', '8', '--max-time', '25', '--retry', '0',
            '-X', method, '-H', 'Authorization: Bearer ' + admin]
    if payload is not None:
        args += ['-H', 'x-control-policy-token: ' + policy,
                 '-H', 'Content-Type: application/json',
                 '--data-binary', json.dumps(payload)]
    args += ['-w', '\nHTTP_STATUS:%{http_code}\n', BASE + path]
    result = subprocess.run(args, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print('CURL_ERROR:', result.stderr[:300])
    return result

r = request('GET', '/v1/jobs/' + JOB)
if r.returncode != 0:
    sys.exit('Network error: no mutation performed')
try:
    body, status = r.stdout.rsplit('\nHTTP_STATUS:', 1)
    job = json.loads(body)
    code = int(status.strip())
except Exception:
    sys.exit('Malformed response: no mutation performed')
if code != 200 or job.get('status') != 'unknown':
    sys.exit('Job is not confirmed unknown: no mutation performed')
print('IMPORTANT: verify the agent is not executing this job.')
with open('/dev/tty', 'r') as tty:
    print('Type YES only after checking execution and approving reconciliation: ', end='', flush=True)
    confirmation = tty.readline().strip()
if confirmation != 'YES':
    sys.exit('Cancelled: no mutation performed')
r = request('POST', '/v1/owner/reconcile',
            {'id': JOB, 'action': 'acknowledge_unknown_no_reexecute'})
if r.returncode != 0:
    sys.exit('Ambiguous POST outcome. Do not retry without GET verification.')
request('GET', '/v1/jobs/' + JOB)