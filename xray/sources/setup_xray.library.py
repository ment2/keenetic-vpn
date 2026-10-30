#!/usr/bin/env python3
"""Build Xray config from a local VLESS subscription; do not print secrets."""
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit, parse_qs, unquote

SRC = Path('/opt/etc/xray/servers.txt')
DEST = Path('/opt/etc/xray/config.json')

def val(q, name, default=''):
    return q.get(name, [default])[0]

def create_outbound(line, n):
    u = urlsplit(line.strip())
    if u.scheme.lower() != 'vless' or not u.hostname or not u.port or not u.username:
        raise ValueError(f'Invalid VLESS URI at entry {n}')
    q = parse_qs(u.query, keep_blank_values=True)
    transport = val(q, 'type', 'tcp').lower()
    security = val(q, 'security', 'none').lower()
    tag = f'vpn{n:02d}'
    name = unquote(u.fragment) or tag
    user = {'id': unquote(u.username), 'encryption': val(q,'encryption','none')}
    if val(q,'flow'):
        user['flow'] = val(q,'flow')
    stream = {'network': transport, 'security': security}
    if security == 'reality':
        if not val(q,'pbk'):
            raise ValueError(f'Missing REALITY public key for entry {n}')
        settings = {'publicKey':val(q,'pbk'), 'shortId':val(q,'sid'), 'serverName':val(q,'sni'), 'fingerprint':val(q,'fp','chrome')}
        if val(q,'spx'): settings['spiderX'] = val(q,'spx')
        stream['realitySettings'] = settings
    elif security == 'tls':
        settings = {'serverName': val(q,'sni') or u.hostname}
        if val(q,'fp'): settings['fingerprint'] = val(q,'fp')
        if val(q,'alpn'): settings['alpn'] = val(q,'alpn').split(',')
        stream['tlsSettings'] = settings
    elif security != 'none':
        raise ValueError(f'Unsupported security mode {security} for entry {n}')
    if transport == 'ws':
        ws = {'path': val(q,'path','/')}
        if val(q,'host'): ws['headers']={'Host':val(q,'host')}
        stream['wsSettings']=ws
    elif transport == 'grpc':
        stream['grpcSettings']={'serviceName':val(q,'serviceName')}
    elif transport == 'xhttp':
        xh = {'path':val(q,'path','/')}
        if val(q,'host'): xh['host']=val(q,'host')
        if val(q,'mode'): xh['mode']=val(q,'mode')
        if val(q,'extra'):
            xh['extra']=json.loads(val(q,'extra'))
        stream['xhttpSettings']=xh
    elif transport != 'tcp':
        raise ValueError(f'Unsupported transport {transport} for entry {n}')
    return {'tag':tag,'protocol':'vless','settings':{'vnext':[{'address':u.hostname,'port':u.port,'users':[user]}]},'streamSettings':stream},name

def main():
    if not SRC.is_file():
        raise SystemExit('Missing /opt/etc/xray/servers.txt')
    lines = [l.strip() for l in SRC.read_text(encoding='utf8').splitlines() if l.strip().startswith('vless://')]
    if not lines:
        raise SystemExit('No VLESS entries found')
    outbounds=[]
    names=[]
    for n,line in enumerate(lines,1):
        out,name=create_outbound(line,n)
        outbounds.append(out)
        names.append((out['tag'],name))
    outbounds.append({'tag':'direct','protocol':'freedom'})
    config={'log':{'loglevel':'warning'},'inbounds':[{'tag':'local-socks','listen':'127.0.0.1','port':10808,'protocol':'socks','settings':{'auth':'noauth','udp':False}}], 'outbounds':outbounds, 'routing':{'domainStrategy':'AsIs','rules':[{'type':'field','inboundTag':['local-socks'],'outboundTag':'vpn01'}]}}
    DEST.parent.mkdir(parents=True,exist_ok=True)
    tmp=DEST.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    os.chmod(tmp,0o600)
    os.replace(tmp,DEST)
    print('Created',DEST,'with',len(lines),'servers; default vpn01')
    print('Available server tags:')
    for tag,name in names:
        print(tag, name)
    print('Only localhost SOCKS :10808 configured; no router traffic routing changed.')

if __name__=='__main__':
    try:
        main()
    except Exception as e:
        print('ERROR:',str(e),file=sys.stderr)
        sys.exit(1)