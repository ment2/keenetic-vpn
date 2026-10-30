# Xray v27: read-only diagnostics approval draft
Date: 2026-10-30

## Confirmed
- read_file /opt/bin/xray-control-v24.py queued, job_id 03a86dac-2047-4fcf-9c02-ae3143a8001a.
- No exec performed; no router changes made.
- Previously inspected v25 watchdog calls xray-control-v24.py status and checks local port; old watchdog may restart Xray.

## Approval-required commands
Run individually only after explicit approval, never while pending read_file needs duplicate submission.

### 1. Process identity and config fingerprint
```sh
/opt/bin/python3 - <<'PY'
from pathlib import Path
import hashlib
for p in Path('/proc').iterdir():
    if not p.name.isdecimal(): continue
    try:
        raw=(p/'cmdline').read_bytes().split(b'\0')
        cmd=[x.decode('utf-8','replace') for x in raw if x]
        if not any('xray' in x.lower() for x in cmd): continue
        stat=(p/'stat').read_text()
        ticks=stat.rsplit(')',1)[1].split()[19]
        print('PID',p.name,'START_TICKS',ticks,'EXECUTABLE',cmd[0] if cmd else '?')
    except (OSError,IndexError,ValueError): pass
f=Path('/opt/etc/xray/config.json')
if f.is_file(): print('CONFIG_SHA256',hashlib.sha256(f.read_bytes()).hexdigest())
else: print('CONFIG_NOT_FOUND')
PY
```

### 2. Redacted structural OpenAI and SOCKS/TPROXY configuration
```sh
/opt/bin/python3 - <<'PY'
import json
from pathlib import Path
p=Path('/opt/etc/xray/config.json')
c=json.loads(p.read_text())
for x in c.get('inbounds',[]):
 print('INBOUND',x.get('tag'),x.get('protocol'),x.get('listen'),x.get('port'), 'SOCKOPT_TPROXY',x.get('streamSettings',{}).get('sockopt',{}).get('tproxy'))
for x in c.get('outbounds',[]):
 print('OUTBOUND',x.get('tag'),x.get('protocol'))
for x in c.get('routing',{}).get('rules',[]):
 print('ROUTING_RULE',x.get('type'),x.get('inboundTag'),x.get('outboundTag'),x.get('balancerTag'))
for x in c.get('routing',{}).get('balancers',[]):
 print('BALANCER',x.get('tag'),x.get('selector'),x.get('fallbackTag'))
PY
```

### 3. Kernel routing and local SOCKS listener (no external probes)
```sh
printf '%s\n' '=== IPV4 RULES ==='; ip -4 rule show
printf '%s\n' '=== IPV4 ROUTES ALL TABLES ==='; ip -4 route show table all
printf '%s\n' '=== IPV6 RULES ==='; ip -6 rule show
printf '%s\n' '=== IPV6 ROUTES ==='; ip -6 route show table all
printf '%s\n' '=== NFT RULESET ==='; if command -v nft >/dev/null 2>&1; then nft list ruleset; else echo 'nft unavailable'; fi
printf '%s\n' '=== IPTABLES MANGLE ==='; if command -v iptables >/dev/null 2>&1; then iptables -t mangle -S; iptables -t filter -S; fi
printf '%s\n' '=== SOCKS LISTENER ==='; netstat -lnt 2>/dev/null | grep '127.0.0.1:10808' || true
```

## Limitations
- Structural config checks do not prove live OpenAI qualification or Telegram VPN egress.
- Fail-closed cannot be established by rules listing alone; a controlled non-disruptive test plan is needed.
- Avoid printing full outbound server addresses, secrets, proxy credentials, Telegram identifiers, and configuration bodies.
- No changes to cron, routes, kill-switch, Xray, watchdog, or startup are authorized.