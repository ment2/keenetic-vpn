"""Actual disposable Mosquitto broker + mixed RC2 synthetic cycle, loopback only."""
import json
import os
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from test_mixed_rc2_integration import BODY, convert, inventory, obs, Cleanup
from mixed_rc2_integration import Store, probe_cycle, publish_shadow, SHADOW, SHADOW_UID


def main():
    links=json.loads(subprocess.check_output(['ip','-j','link','show']))
    assert {x['ifname'] for x in links}=={'lo'},'loopback-only namespace required'
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix='rc2-broker-') as td:
        d=Path(td);p=d/'rc2-mixed-shadow';p.mkdir(mode=0o700);store=Store(p)
        # Default Mosquitto local-only mode; no config file outside private state.
        # The namespace guard above also prohibits all non-loopback interfaces.
        broker=subprocess.Popen(['mosquitto','-p',str(port)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        sub=None
        try:
            end=time.monotonic()+5
            while time.monotonic()<end:
                if broker.poll() is not None:raise RuntimeError('synthetic broker exited: '+broker.stderr.read(2048).decode(errors='replace'))
                try:
                    with socket.create_connection(('127.0.0.1',port),timeout=.2):break
                except OSError:time.sleep(.1)
            else:raise RuntimeError('broker did not listen')
            args=['mosquitto_sub','-h','127.0.0.1','-p',str(port),'-q','1','-t','#','-F','%t\t%p','-W','25','-C','110']
            sub=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            time.sleep(.5)
            now=int(time.time());probe_cycle(store,fetch=lambda:BODY,converter=convert,inventory=inventory,probe=lambda o:obs(now,'RU' if o['tag']=='hy01' else 'LT'),cleanup_error=Cleanup,verify=lambda:None,idle=lambda:True,minute=3)
            assert publish_shadow(store,active_reader=lambda:{'outbounds':[]},pending_reader=lambda:{'outbounds':[]},inventory=inventory,broker_port=port,include_history=True)==12
            out,err=sub.communicate(timeout=30);assert sub.returncode==0
            messages=[(t,json.loads(p)) for t,p in (x.split('\t',1) for x in out.decode().splitlines())]
            assert len(messages)==110
            agg=[p for t,p in messages if t==SHADOW+'aggregate'];assert len(agg)==1 and agg[0]['count']==12 and agg[0]['probe_complete']==12
            assert [r['geo_policy'] for r in agg[0]['rows'][-2:]]==['EXCLUDED_RU','ALLOWED']
            assert all(t.startswith(SHADOW) or t.startswith('homeassistant/sensor/'+SHADOW_UID) for t,_ in messages)
            assert 'synthetic-' not in out.decode()
            # Reconnect: only discovery retained; states/aggregate must not be replayed.
            retained=subprocess.run(['mosquitto_sub','-h','127.0.0.1','-p',str(port),'-q','1','-t','#','-F','%r\t%t','-C','97','-W','8'],capture_output=True,timeout=10,check=True).stdout.decode().splitlines()
            assert len(retained)==97 and all(line.startswith('1\thomeassistant/sensor/'+SHADOW_UID) for line in retained)
            print('MOSQUITTO_LAB_PASS 12 nodes 110 publications 97 retained discovery 13 nonretained states',flush=True)
        finally:
            for proc in (sub,broker):
                if proc is not None and proc.poll() is None:
                    proc.terminate()
                    try:proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=3)

if __name__=='__main__':main()
