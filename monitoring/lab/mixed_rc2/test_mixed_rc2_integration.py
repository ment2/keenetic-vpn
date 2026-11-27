import base64
import copy
import datetime
import hashlib
import json
import os
import socket
import struct
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.parse import urlsplit
from jinja2 import Environment, StrictUndefined
from mixed_rc2_candidate import build, generation
from mixed_rc2_integration import (Store, Busy, Deadline, probe_cycle, scheduled_shadow, render, publication, history, aggregate, identity, METRICS, EXTRA, SHADOW, SHADOW_UID, SHADOW_EID, ShadowMQTT, publish_shadow, safe_pool, pool_from_config, sha, encoded, fetch_full, PROBE_BUDGET, FETCH_BUDGET, HISTORY_BUDGET, CYCLE_BUDGET, PER_NODE)
from mixed_rc2_cards import overview, graphs, view, plan_dashboard, rollback_dashboard

try:
    from monitoring.vpn_inventory import inventory as actual_inventory
    from monitoring.rc2_history import messages as old_messages
    from monitoring.rc2_snapshot import generation as old_generation
except ImportError:
    actual_inventory=old_messages=old_generation=None

V=['vless://synthetic@v%d.example:443'%i for i in range(10)]
H=['hy2://synthetic-auth@hy.example:443?sni=hy.example','hysteria2://synthetic-pass@lt.example:443?obfs=salamander&obfs-password=synthetic-mask']
BODY=base64.b64encode('\n'.join(V+H).encode())

def convert(uri,i):
    u=urlsplit(uri);return {'tag':'vpn%02d'%i,'protocol':'vless','settings':{'vnext':[{'address':u.hostname,'port':u.port,'users':[{'id':'synthetic-uuid','flow':'xtls-rprx-vision'}]}]},'streamSettings':{'network':'tcp','security':'tls'}},None

def inventory(cfg):
    if actual_inventory:return actual_inventory(cfg)
    result=[]
    for o in cfg['outbounds']:
        s=o['settings']['vnext'][0];st=o['streamSettings'];canon=[s['address'].rstrip('.').lower(),s['port'],st['network'],st['security'],'',s['users'][0]['flow']]
        node='node_'+hashlib.sha256(json.dumps(canon,ensure_ascii=True,separators=(',',':')).encode()).hexdigest()[:20]
        result.append({'node_id':node,'tag':o['tag']})
    return result

def obs(at=1000,country='LT',ip='8.8.8.8'):
    d={k:{'status':'ok','route_verified':True,'checked_at':at,'duration_ms':42} for k in ('internet','openai','exit_ip','geo')}
    d['exit_ip']['ip']=ip;d['geo'].update(ip=ip,country=country,city='Vilnius');return d

class Cleanup(Exception):pass

class FakeBroker:
    """Loopback wire fixture; checks actual CONNECT/PUBLISH/PUBACK and retain bit."""
    def __init__(self):
        self.listener=socket.socket();self.listener.bind(('127.0.0.1',0));self.listener.listen();self.listener.settimeout(4);self.port=self.listener.getsockname()[1];self.received=[];self.err=None
        self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start()
    def run(self):
        try:
            with self.listener.accept()[0] as c:
                c.settimeout(4)
                def exact(n):
                    out=b''
                    while len(out)<n:
                        part=c.recv(n-len(out))
                        if not part:raise EOFError()
                        out+=part
                    return out
                def frame():
                    kind=exact(1)[0];n=0;m=1
                    while True:
                        a=exact(1)[0];n+=(a&127)*m
                        if a<128:break
                        m*=128
                    return kind,exact(n)
                k,b=frame();assert k==0x10 and b.startswith(b'\x00\x04MQTT');c.sendall(b'\x20\x02\x00\x00')
                while True:
                    k,b=frame()
                    if k==0xe0:break
                    assert k in (0x32,0x33);n=struct.unpack('!H',b[:2])[0];topic=b[2:2+n].decode();pid=b[2+n:4+n];data=json.loads(b[4+n:]);self.received.append((topic,data,k==0x33));c.sendall(b'\x40\x02'+pid)
        except BaseException as e:self.err=e
        finally:self.listener.close()
    def done(self):
        self.thread.join(6)
        if self.thread.is_alive():raise AssertionError('broker still running')
        if self.err:raise self.err

class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);p=Path(self.temp.name)/'rc2-mixed-shadow';p.mkdir(mode=0o700);self.store=Store(p);self.now=1000;self.mono=0;self.fetches=0
    def fetch(self):self.fetches+=1;return BODY
    def cycle(self,**changes):
        kw=dict(fetch=self.fetch,converter=convert,inventory=inventory,probe=lambda o:obs(self.now),cleanup_error=Cleanup,verify=lambda:None,idle=lambda:True,clock=lambda:self.now,mono=lambda:self.mono,minute=3);kw.update(changes);return probe_cycle(self.store,**kw)
    def snapshot(self):return render(self.store.read(),{}, {},self.now)
    def test_end_to_end(self):
        self.cycle();p=self.snapshot();self.assertEqual(self.fetches,1);self.assertEqual(p['count'],12);self.assertEqual(p['probe_complete'],12);self.assertEqual(p['protocol_counts'],{'vless':10,'hysteria2':2});self.assertTrue(all(r['eligible'] for r in p['rows']));self.assertNotIn('synthetic-',json.dumps(p));self.assertEqual(self.store.current.stat().st_mode&0o777,0o600)
    def test_two_generations_rollback(self):
        a=self.cycle();self.now=1900;b=self.cycle(probe=lambda o:obs(self.now,'RU'));self.assertNotEqual(a,b);self.assertEqual(self.snapshot()['rows'][-1]['geo_policy'],'EXCLUDED_RU');self.assertEqual(self.store.rollback(b,a),a);self.assertEqual(self.snapshot()['rows'][-1]['geo_policy'],'ALLOWED');self.assertRaises(Busy,self.store.rollback,b,a)
    def test_cleanup_no_commit(self):
        a=self.cycle()
        def fail(o):raise Cleanup()
        self.assertRaises(Cleanup,self.cycle,probe=fail);self.assertEqual(sha(self.store.read_raw()),a)
    def test_updater_busy_no_commit(self):
        a=self.cycle();flags=iter([True,True,False]);self.assertRaises(Busy,self.cycle,idle=lambda:next(flags));self.assertEqual(sha(self.store.read_raw()),a)
    def test_bad_fetch_no_commit(self):
        a=self.cycle();self.assertRaises(ValueError,self.cycle,fetch=lambda:b'invalid');self.assertEqual(sha(self.store.read_raw()),a)
    def test_source_verify_no_commit(self):
        a=self.cycle();count=0
        def verify():
            nonlocal count;count+=1
            if count==2:raise ValueError('pin mismatch')
        self.assertRaises(ValueError,self.cycle,verify=verify);self.assertEqual(sha(self.store.read_raw()),a)
    def test_over_capacity(self):
        self.assertRaises(ValueError,self.cycle,fetch=lambda:'\n'.join(V+H+['hy2://pw@third.example:443']).encode());self.assertIsNone(self.store.read())
    def test_schedule_and_lock(self):
        self.assertRaises(Busy,self.cycle,minute=4)
        with self.store.lock():self.assertRaises(Busy,self.cycle)
        self.assertEqual(self.fetches,0)
    def test_timing(self):
        self.assertGreaterEqual(PROBE_BUDGET,12*PER_NODE);self.assertLessEqual(FETCH_BUDGET+PROBE_BUDGET+HISTORY_BUDGET,CYCLE_BUDGET);self.assertLess(CYCLE_BUDGET,900)
        def slow(o):self.mono+=PER_NODE;return obs()
        self.cycle(probe=slow);self.assertEqual(self.snapshot()['probe_complete'],12)
    def test_scheduled_slot(self):
        self.now=1080; broker=FakeBroker()
        args=dict(fetch=self.fetch,converter=convert,inventory=inventory,probe=lambda o:obs(self.now),cleanup_error=Cleanup,verify=lambda:None,idle=lambda:True,active_reader=lambda:{'outbounds':[]},pending_reader=lambda:{'outbounds':[]},broker_port=broker.port,clock=lambda:self.now,mono=lambda:self.mono,sleep=lambda _:None,minute=18)
        token,count=scheduled_shadow(self.store,**args);broker.done();self.assertEqual(count,12);self.assertEqual(sha(self.store.read_raw()),token)
        self.assertRaises(Busy,scheduled_shadow,self.store,**args)
        self.now=1995;self.assertRaises(Busy,scheduled_shadow,self.store,**args)
        self.assertEqual(self.fetches,1)
    def test_rollback_publication_lock(self):
        a=self.cycle();self.now=1900;b=self.cycle()
        with self.store.lock('publish'):self.assertRaises(Busy,self.store.rollback,b,a)
        self.assertEqual(sha(self.store.read_raw()),b)
    def test_budget_partial_no_inherited_success(self):
        self.cycle();self.now=1900
        def slow(o):self.mono+=100;return obs(self.now)
        self.cycle(probe=slow);p=self.snapshot();self.assertLess(p['probe_complete'],12);self.assertTrue(any(r['vpn']['status']=='missing' for r in p['rows']))
    def test_geo_rules(self):
        def p(o):return obs(country='BY' if o['tag']=='hy01' else 'RU' if o['tag']=='hy02' else 'LT')
        self.cycle(probe=p);r=self.snapshot()['rows'];self.assertEqual([x['geo_policy'] for x in r[-2:]],['EXCLUDED_BY','EXCLUDED_RU']);self.assertFalse(any(x['eligible'] for x in r[-2:]))
    def test_stale(self):
        self.cycle();self.now+=1801;self.assertEqual(self.snapshot()['inventory_status'],'unavailable')
    def test_membership(self):
        self.cycle();b=self.store.read();cfg={'outbounds':[x['outbound'] for x in b['records'][:4]]};active=pool_from_config(cfg,inventory);p=render(b,active,{},1000);self.assertEqual(sum(r['active'] for r in p['rows']),4);self.assertTrue(all(r['active_config_matches'] for r in p['rows'][:4]));self.assertFalse(p['rows'][-1]['active']);self.assertIsNone(safe_pool(lambda:{'outbounds':[b['records'][-1]['outbound']]},inventory))
    def test_last_geo(self):
        self.cycle();self.now+=900;self.cycle(probe=lambda o:{});r=self.snapshot()['rows'][-1];self.assertEqual(r['last_geo']['country'],'LT');self.assertEqual(r['geo_policy'],'UNVERIFIED')
    def test_unsupported(self):
        self.cycle(fetch=lambda:'\n'.join(V+H[:1]+['hy2://pw@lt.example?insecure=1']).encode());r=self.snapshot()['rows'][-1];self.assertEqual(r['vpn']['status'],'unsupported');self.assertFalse(r['eligible']);self.assertEqual(history(r,1000)[1][1]['vpn'],'unsupported')
    def test_private_symlink(self):
        self.store.current.symlink_to('/etc/passwd');self.assertRaises(OSError,self.store.read)
    def test_provider_fetch(self):
        def runner(args,**kw):
            self.assertNotIn('private.example',repr(args));self.assertIn(b'https://private.example',kw['input']);self.assertIn('=https',args);return type('Result',(),{'returncode':0,'stdout':BODY})()
        self.assertEqual(fetch_full('https://private.example/abc',runner=runner),BODY);self.assertRaises(ValueError,fetch_full,'http://private.example',runner=runner)
    def test_mqtt_plan(self):
        self.cycle();p=self.snapshot();d,s=publication(p,1000);self.assertEqual(len(d),97);self.assertEqual(len(s),13);self.assertTrue(all(x[2] for x in d));self.assertFalse(any(x[2] for x in s));self.assertGreater(len(encoded(s[0][1])),4096);self.assertLessEqual(len(encoded(s[0][1])),32768);self.assertTrue(all(SHADOW_UID in x[0] for x in d));self.assertNotIn('synthetic-',json.dumps((d,s)))
    def test_mqtt_wire(self):
        self.cycle();b=FakeBroker();n=publish_shadow(self.store,active_reader=lambda:{'outbounds':[]},pending_reader=lambda:{'outbounds':[]},inventory=inventory,broker_port=b.port,include_history=True,clock=lambda:1000,sleep=lambda _:None);b.done();self.assertEqual(n,12);self.assertEqual(len(b.received),110);self.assertEqual(sum(x[2] for x in b.received),97);self.assertEqual(b.received[97][1]['count'],12)
    def test_minute_publish(self):
        self.cycle();b=FakeBroker();publish_shadow(self.store,active_reader=lambda:{'outbounds':[]},pending_reader=lambda:{'outbounds':[]},inventory=inventory,broker_port=b.port,clock=lambda:1000);b.done();self.assertEqual(len(b.received),2)
    def test_shadow_rejects_live(self):
        self.assertRaises(PermissionError,ShadowMQTT,'192.168.0.169',1883,time.monotonic()+2);b=FakeBroker()
        with ShadowMQTT('127.0.0.1',b.port,time.monotonic()+2) as m:self.assertRaises(PermissionError,m.publish,'keenetic/vpn-monitor/v1/dynamic_rc2',{},False)
        b.done();self.assertEqual(b.received,[])
    def test_history_ids(self):
        self.cycle();r=self.snapshot()['rows'][0];d,s=history(r,1000,False);self.assertEqual(s[0],'keenetic/vpn-monitor/v1/'+r['id']+'/rc2_history');self.assertTrue(all(x[1]['default_entity_id'].startswith('sensor.keenetic_rc2_') for x in d));self.assertEqual(len(d),8)
    @unittest.skipUnless(old_messages,'requires actual repository baseline')
    def test_exact_legacy_history_contract(self):
        self.cycle();b=self.store.read();p=self.snapshot()
        for r,o in zip(p['rows'][:10],b['records'][:10]):
            self.assertEqual(o['generation'],old_generation(o['outbound']));d,_=history(r,1000,False);old=list(old_messages(r['id'],r['tag'],{m:1620 for m in METRICS}));self.assertEqual([(x[0],x[1]) for x in d[:6]],old)
    def test_cards_and_rollback(self):
        self.cycle();p=self.snapshot();d,_=publication(p,1000);states=[]
        for _,x,_ in d[1:]:
            eid=x['default_entity_id'];node,metric=next((r['id'],m) for r in p['rows'] for m in {**METRICS,**EXTRA} if eid==SHADOW_EID+r['id']+'_'+m);states.append({'entity_id':eid,'attributes':{'node_id':node,'metric':metric}})
        individual,hist=graphs(p['rows'],states);self.assertEqual(len(individual),12);self.assertEqual(len(hist),6);self.assertEqual(sum(x['type']=='custom:rc2-history-legend' for x in hist),4);self.assertTrue(all(len(x.get('graph',x)['entities'])==12 for x in hist));self.assertRaises(ValueError,graphs,p['rows'],states[:-8]);v=view(p['rows'],states);old={'views':[{'path':'rc2-mixed-shadow','title':'keep','cards':[]},{'path':'other','cards':[{'type':'markdown'}]}],'extra':'keep'};plan=plan_dashboard(old,'rc2-mixed-shadow',v,sha(encoded(old)));self.assertEqual(plan['after']['views'][1],old['views'][1]);self.assertEqual(rollback_dashboard(plan['after'],plan),old);self.assertRaises(ValueError,rollback_dashboard,old,plan)
    def test_card_render(self):
        self.cycle();p=self.snapshot();env=Environment(undefined=StrictUndefined);tmpl=env.from_string(overview()['content']);dt=lambda t:datetime.datetime.fromtimestamp(t,datetime.timezone.utc);kw=dict(state_attr=lambda eid,k:p.get(k),states=lambda eid:'ok',now=lambda:dt(1000),as_timestamp=lambda d:d.timestamp(),as_local=lambda d:d,as_datetime=dt);s=tmpl.render(**kw);self.assertIn('Подключений: 12',s);self.assertIn('Hysteria2 2',s);self.assertIn('hy02',s);self.assertIn('42 мс',s);self.assertNotIn('synthetic-',s);kw['now']=lambda:dt(1200);self.assertIn('Нет актуальной',tmpl.render(**kw))

if __name__=='__main__':unittest.main()
