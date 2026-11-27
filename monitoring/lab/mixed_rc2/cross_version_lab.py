"""Disposable localhost-only Hysteria2 interoperability test. No real subscription."""
import argparse
from urllib.parse import quote
import copy
import http.server
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from unittest.mock import patch
from mixed_rc2_candidate import hy2


def run(cmd, **kwargs):
    return subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30, **kwargs)


def port(kind):
    with socket.socket(socket.AF_INET, kind) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def stop(p):
    if p.poll() is None:
        p.terminate()
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait(timeout=5)


class Witness(http.server.BaseHTTPRequestHandler):
    hits = []
    def log_message(self, *_): pass
    def do_GET(self):
        self.hits.append(self.path)
        bodies = {'/exit_ip': {'ip': '8.8.8.8'}, '/geo': {'success': True, 'ip': '8.8.8.8', 'country_code': 'LT', 'city': 'Vilnius'}}
        if self.path in bodies:
            self.send_response(200)
            b = json.dumps(bodies[self.path]).encode()
            self.send_header('Content-Length', str(len(b)))
            self.end_headers(); self.wfile.write(b)
        else:
            self.send_response(204 if self.path == '/internet' else 401 if self.path == '/openai' else 404)
            self.end_headers()


def main():
    a = argparse.ArgumentParser()
    a.add_argument('--xray', required=True)
    a.add_argument('--hysteria', required=True)
    a.add_argument('--qemu')
    args = a.parse_args()
    # Hard guard: this script is only run in a private network namespace with loopback.
    if {link['ifname'] for link in json.loads(subprocess.check_output(['ip','-j','link','show']))} != {'lo'}:
        raise SystemExit('lab requires isolated loopback-only network namespace')
    from monitoring import rc2_probe
    from monitoring.isolated_pair_probe import config_for
    xray = Path(args.xray).resolve(); hysteria = Path(args.hysteria).resolve()
    with tempfile.TemporaryDirectory(prefix='mixed-rc2-lab-') as td:
        d = Path(td)
        cert, key = d/'cert.pem', d/'key.pem'
        run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost','-addext','basicConstraints=critical,CA:TRUE','-keyout',str(key),'-out',str(cert)])
        exe = xray
        if args.qemu:
            exe = d/'xray-qemu'
            import shlex
            exe.write_text('#!/bin/sh\nexec '+shlex.quote(str(Path(args.qemu).resolve()))+' '+shlex.quote(str(xray))+' "$@"\n')
            exe.chmod(0o700)
        run([str(exe), 'version'])
        httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Witness)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True); thread.start()
        urls = {k:'http://127.0.0.1:%d/%s' % (httpd.server_port,k) for k in ('internet','openai','exit_ip','geo')}
        try:
            for masked in (False, True):
                udp = port(socket.SOCK_DGRAM)
                srv = {'listen': '127.0.0.1:%d'%udp, 'tls': {'cert': str(cert), 'key': str(key)}, 'auth': {'type': 'password', 'password': 'synthetic-only'}}
                query = '?sni=localhost'
                if masked:
                    srv['obfs'] = {'type':'salamander','salamander':{'password':'synthetic-mask'}}
                    query += '&obfs=salamander&obfs-password=synthetic-mask'
                sp = d/'server.json'; sp.write_text(json.dumps(srv)); sp.chmod(0o600)
                with (d/'server.log').open('wb') as log:
                    proc = subprocess.Popen([str(hysteria),'server','-c',str(sp)],stdout=log,stderr=subprocess.STDOUT)
                    try:
                        end=time.monotonic()+8
                        while time.monotonic()<end:
                            if proc.poll() is not None: raise RuntimeError('server exited')
                            with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
                                try: s.bind(('127.0.0.1',udp))
                                except OSError: break
                            time.sleep(.1)
                        else: raise RuntimeError('server did not bind')
                        if masked:
                            fm={'udp':[{'type':'salamander','settings':{'password':'synthetic-mask'}}],'quicParams':{'congestion':'bbr','keepAlivePeriod':15,'maxIdleTimeout':60}}
                            query+='&fm='+quote(json.dumps(fm),safe='')
                        outbound=hy2('hy2://synthetic-only@127.0.0.1:%d'%udp+query,'hy01')
                        conf=d/'test.json'; conf.write_text(json.dumps(config_for(outbound,port(socket.SOCK_STREAM)))); conf.chmod(0o600)
                        with patch.dict(os.environ, {'SSL_CERT_FILE':str(cert)}):
                            run([str(exe),'run','-test','-config',str(conf)])
                            with patch.multiple(rc2_probe, XRAY=str(exe), CURL=shutil.which('curl'), URLS=urls):
                                Witness.hits.clear()
                                result=rc2_probe.probe_node(outbound)
                                assert set(Witness.hits)=={'/internet','/openai','/exit_ip','/geo'}, Witness.hits
                                assert all(result[k]['status']=='ok' and result[k]['route_verified'] and result[k]['duration_ms']>=0 for k in urls), result
                                assert result['geo']['country']=='LT'
                                print('POSITIVE', 'salamander' if masked else 'plain', 'all four owned observations',flush=True)
                                if not masked:
                                    for case in ('auth','tls'):
                                        wrong=copy.deepcopy(outbound)
                                        if case=='auth': wrong['streamSettings']['hysteriaSettings']['auth']='incorrect'
                                        else: wrong['streamSettings']['tlsSettings']['serverName']='wrong.invalid'
                                        Witness.hits.clear(); result=rc2_probe.probe_node(wrong)
                                        assert not Witness.hits and not any(v['status']=='ok' for v in result.values()), result
                                        print('NEGATIVE',case,'no HTTP witness',flush=True)
                                if masked:
                                    for case in ('wrong_mask','no_mask'):
                                        wrong=copy.deepcopy(outbound)
                                        stream=wrong['streamSettings']
                                        if case=='wrong_mask': stream['finalmask']['udp'][0]['settings']['password']='incorrect'
                                        else: stream.pop('finalmask')
                                        Witness.hits.clear(); result=rc2_probe.probe_node(wrong)
                                        assert not Witness.hits and not any(v['status']=='ok' for v in result.values()), result
                                        print('NEGATIVE',case,'no HTTP witness',flush=True)
                    finally:
                        stop(proc)
        finally:
            httpd.shutdown(); httpd.server_close(); thread.join(timeout=3)
    print('LOOPBACK_LAB_PASS', 'mips32le-qemu-user' if args.qemu else 'amd64')

if __name__=='__main__': main()
