#!/opt/bin/python3
"""Read-only local Keenetic agent ledger inventory; does not query Cloudflare."""
import json
import pathlib
import re
base = pathlib.Path('/opt/telegram-ai')
paths = [base / 'keenetic-agent-pending-result.json']
ledger = base / 'keenetic-agent-ledger'
if ledger.is_dir():
    paths += sorted(p for p in ledger.iterdir() if p.is_file())
uuid = re.compile(r'[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}', re.I)
for p in paths:
    if not p.exists():
        continue
    ids = set(uuid.findall(p.name))
    try:
        data = json.loads(p.read_text())
        if isinstance(data, dict):
            for key in ('job_id', 'id'):
                if isinstance(data.get(key), str):
                    ids.update(uuid.findall(data[key]))
            state = data.get('state', data.get('status', '?'))
        else:
            state = '?'
    except Exception:
        state = 'unreadable'
    for job_id in sorted(ids):
        print('ID:', job_id, '| LOCAL_STATE:', state, '| SOURCE:', p.name)
print('LOCAL_SCAN_COMPLETE')