"""RC2 mixed shadow integration. No production entry point or deployment code.
Inputs are injected; only a private lab state directory and loopback MQTT may be written.
Production identity plan is pure data, never accepted by the shadow transport.
"""
import contextlib
import copy
import fcntl
import hashlib
import ipaddress
import json
import os
import re
import socket
import stat
import sys
import runpy
import struct
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import urlsplit
from mixed_rc2_candidate import build, collect, generation, payload, rows, observation, FRESH

MAX_NODES = 12  # acceptance capacity, not a truncation rule
PROBE_BUDGET = 690
HISTORY_BUDGET = 120
CYCLE_BUDGET = 885
PER_NODE = 55
FETCH_BUDGET = 65
SETTLE = 5
EXPIRY_GUARD = 180
START_MINUTES = {3, 18, 33, 48}
METRICS = {'vpn':'VPN witness','internet':'Internet HTTP 204','openai':'OpenAI HTTP 401','geo':'Geolocation','internet_ms':'Internet probe duration','openai_ms':'OpenAI probe duration'}
EXTRA = {'geo_policy':'Geo policy','eligible':'Pool eligibility'}
PREFIX = 'keenetic/vpn-monitor/v1/'
SHADOW = PREFIX + 'rc2_mixed_shadow/'
DISCOVERY = 'homeassistant/sensor/'
SHADOW_UID = 'keenetic6059_rc2mix_shadow_'
PROD_UID = 'keenetic6059_rc2_'
SHADOW_EID = 'sensor.keenetic_rc2mix_shadow_'
PROD_EID = 'sensor.keenetic_rc2_'
NODE = re.compile(r'(?:node_|hy2_)[a-f0-9]{20}\Z')
TAG = re.compile(r'(?:vpn|hy)[0-9]{2,3}\Z')

class Busy(RuntimeError): pass
class Deadline(RuntimeError): pass


def fetch_full(url, *, runner=subprocess.run):
    """One HTTPS response; no URL in argv, no curl config/env proxy overrides.
    Caller supplies URL privately in a separately approved device adapter.
    No exception text or response is printed. No file writes by this function.
    """
    u = urlsplit(url)
    if u.scheme != 'https' or not u.hostname or any(ord(c)<33 or ord(c)==127 or c in '\\"' for c in url):
        raise ValueError('invalid HTTPS subscription locator')
    env={k:v for k,v in os.environ.items() if k.lower() not in ('http_proxy','https_proxy','all_proxy','no_proxy')}
    result=runner(['/opt/bin/curl','-q','--config','-','--fail','--silent','--location','--proto','=https','--proto-redir','=https','--connect-timeout','10','--max-time','60','--max-filesize','1048576','--noproxy','*'],input=('url = "'+url+'"\n').encode(),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=FETCH_BUDGET,env=env)
    if result.returncode or not 1<=len(result.stdout)<=1048576:
        raise ValueError('provider response unavailable')
    return result.stdout


def pool_from_config(config, inventory):
    """Actual VLESS membership by existing identity and generation; no mutation."""
    if not isinstance(config,dict) or not isinstance(config.get('outbounds'),list): raise ValueError('invalid pool')
    result={}
    for o in config['outbounds']:
        if o.get('protocol')=='vless':
            e=inventory({'outbounds':[o]})
            if len(e)!=1: raise ValueError('invalid VLESS pool')
            node=e[0]['node_id']
        elif o.get('protocol')=='hysteria':
            # Current production pool is VLESS-only. Future native HY2 membership
            # requires explicit canonical matching review; never assert false membership.
            raise ValueError('unreviewed Hysteria pool')
        else: continue
        if not NODE.fullmatch(node) or node in result: raise ValueError('duplicate or invalid pool ID')
        result[node]=generation(o)
    return result


def safe_pool(reader, inventory, optional=False):
    try: return pool_from_config(reader(), inventory)
    except FileNotFoundError: return {} if optional else None
    except (OSError,ValueError,TypeError,KeyError,AttributeError): return None


def encoded(data): return json.dumps(data,ensure_ascii=True,separators=(',',':'),sort_keys=True).encode()

def sha(data): return hashlib.sha256(data).hexdigest()


def regular_read(path):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as f:
        s=os.fstat(f.fileno())
        if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.geteuid() or s.st_mode&0o077: raise PermissionError('private state required')
        return f.read(4*1024*1024+1)


def atomic(path,data):
    fd,name=tempfile.mkstemp(prefix='.rc2mix-',dir=str(path.parent))
    try:
        with os.fdopen(fd,'wb') as f: f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(name,path)
        d=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try: os.fsync(d)
        finally: os.close(d)
    finally:
        if os.path.exists(name): os.unlink(name)


class Store:
    def __init__(self, path):
        p=Path(path)
        if p.is_symlink(): raise PermissionError('symlink state directory')
        self.path=p.resolve(strict=True)
        s=self.path.stat()
        # Lab path only, not current RC2 or Xray directories.
        if self.path.name!='rc2-mixed-shadow' or not self.path.is_dir() or s.st_uid!=os.geteuid() or s.st_mode&0o077 or str(self.path).startswith(('/opt/etc/','/opt/var/lib/vpn-monitor/','/config/')):
            raise PermissionError('private shadow state directory required')
        self.current=self.path/'current.json';self.previous=self.path/'previous.json'
    @contextlib.contextmanager
    def lock(self, name='cycle'):
        if name not in ('cycle','publish','schedule'): raise ValueError('invalid lock name')
        fd=os.open(self.path/(name+'.lock'),os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK,0o600)
        with os.fdopen(fd,'rb') as f:
            s=os.fstat(f.fileno())
            if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.geteuid() or s.st_mode&0o077: raise PermissionError('unsafe lock')
            try: fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError: raise Busy('shadow lock busy') from None
            yield
    def read_raw(self):
        try: return regular_read(self.current)
        except FileNotFoundError: return None
    def read(self):
        raw=self.read_raw()
        if raw is None: return None
        if len(raw)>4*1024*1024: raise ValueError('state too large')
        return json.loads(raw)
    def commit(self,data,expected):
        old=self.read_raw()
        if (sha(old) if old is not None else None)!=expected: raise Busy('state changed')
        b=encoded(data)
        if len(b)>4*1024*1024: raise ValueError('state too large')
        if old is not None: atomic(self.previous,old)
        atomic(self.current,b)
        if self.read_raw()!=b: raise RuntimeError('state readback failed')
        return sha(b)
    def rollback(self,expected_current,expected_previous):
        with self.lock('schedule'), self.lock(), self.lock('publish'):
            old=self.read_raw(); prev=regular_read(self.previous)
            if old is None or sha(old)!=expected_current or sha(prev)!=expected_previous: raise Busy('rollback compare-and-swap failed')
            # rollback to verified previous state; preserve displaced state separately
            atomic(self.path/'displaced.json',old);atomic(self.current,prev)
            if self.read_raw()!=prev: raise RuntimeError('rollback readback failed')
            return sha(prev)


def render(bundle, active, pending, now):
    if not bundle: return {'schema':2,'checked_at':now,'inventory_status':'unavailable','count':0,'rows':[]}
    data=payload(bundle['records'],bundle['cache'],active,now,bundle['subscription_at'],pending)
    data.setdefault('checked_at',now)
    # Maintain previous RC2 last_geo only with matching config and exit IP.
    if data['inventory_status']=='ok':
        for r in data['rows']:
            c=bundle['cache'].get(r['id'],{})
            last=observation(c.get('last_geo'),'geo',now)
            raw=c.get('last_geo')
            if last['status']=='stale' and isinstance(raw,dict) and 0<=now-raw.get('checked_at',-1)<=86400:
                # Validate content with original measurement time, not current time.
                last=observation(raw,'geo',raw['checked_at'])
            if r['geo']['status']!='ok' and last['status']=='ok' and (not r['exit_ip'] or r['exit_ip']==last.get('ip')):
                r['last_geo']=last
        if len(encoded(data))>32768: raise ValueError('aggregate capacity')
    return data


def probe_cycle(store, *, fetch, converter, inventory, probe, cleanup_error, verify, idle, clock=time.time, mono=time.monotonic, minute=None):
    """Single generation, one provider fetch, sequential owned probes; no MQTT.
    Separate publish phase may see previous complete generation, never partial writes.
    `verify` checks reviewed source pins before and after the provider/probes.
    `idle` observes existing updater lock; never writes/locks production.
    """
    minute=time.localtime().tm_min if minute is None else minute
    if minute not in START_MINUTES or not idle(): raise Busy('not scheduled or updater busy')
    with store.lock():
        start=mono(); oldraw=store.read_raw(); old=store.read() or {}; verify()
        body=fetch(); stamp=int(clock()); records=build(body,converter,inventory); del body
        if len(records)>MAX_NODES: raise ValueError('capacity exceeded; generation rejected, not truncated')
        verify()
        if not idle(): raise Busy('updater busy after fetch')
        deadline=min(start+FETCH_BUDGET+PROBE_BUDGET,mono()+PROBE_BUDGET)
        def guarded(outbound):
            if not idle(): raise Busy('updater busy during probes')
            return probe(outbound)
        # Busy must propagate just like a cleanup failure, not become a missing probe.
        cache=collect(records,guarded,deadline,mono,(cleanup_error,Busy))
        for r in records:
            c=cache.setdefault(r['id'],{'generation':r['generation'],'observations':{}})
            oldc=old.get('cache',{}).get(r['id'],{})
            prior=oldc.get('last_geo') if oldc.get('generation')==r['generation'] else None
            raw=c['observations']; g=raw.get('geo'); ip=observation(raw.get('exit_ip'),'exit_ip',int(clock()))
            clean=observation(g,'geo',int(clock()))
            if clean['status']=='ok' and ip['status']=='ok' and ip.get('ip')==clean.get('ip') and abs(ip['at']-clean['at'])<=55: prior=g
            if prior and (not isinstance(prior,dict) or type(prior.get('checked_at')) is not int or not 0<=clock()-prior['checked_at']<=86400 or (ip['status']=='ok' and ip.get('ip')!=prior.get('ip'))): prior=None
            c['last_geo']=prior
        verify()
        if mono()-start>FETCH_BUDGET+PROBE_BUDGET or not idle(): raise Deadline('probe phase exceeded budget or updater busy')
        bundle={'subscription_at':stamp,'records':records,'cache':cache}
        # Refuse publication overflow before replacing known-good bundle.
        render(bundle,{}, {},int(clock()))
        return store.commit(bundle,sha(oldraw) if oldraw is not None else None)


def identity(row,metric,shadow):
    n,t=row['id'],row['tag']
    if not NODE.fullmatch(n) or not TAG.fullmatch(t) or (n.startswith('node_') != t.startswith('vpn')) or metric not in {**METRICS,**EXTRA}: raise ValueError('invalid history identity')
    uid=(SHADOW_UID if shadow else PROD_UID)+n+'_'+metric
    eid=(SHADOW_EID if shadow else PROD_EID)+n+'_'+metric
    topic=(SHADOW+n+'/history') if shadow else PREFIX+n+'/rc2_history'
    return uid,eid,topic


def history(row,now,shadow=True):
    """Six legacy metrics retain byte-equivalent identity in cutover plan;
    extra policy metrics additive. Shadow uses entirely disjoint names/topics.
    """
    discovery=[]; state={'node_id':row['id'],'tag':row['tag']}
    for metric,label in {**METRICS,**EXTRA}.items():
        uid,eid,topic=identity(row,metric,shadow)
        key=metric.removesuffix('_ms')
        obs=row[key] if metric in METRICS else row['geo']
        at=obs.get('at'); remaining=int(FRESH-(now-at)) if type(at) is int and 0<=now-at<=FRESH else 0
        value=(obs['ms'] if metric.endswith('_ms') else obs['status']) if metric in METRICS else row[metric]
        # Explicit unsupported has no measurement timestamp; no fake fresh success.
        if row.get('support')=='unsupported': value=None if metric.endswith('_ms') else 'UNVERIFIED' if metric=='geo_policy' else False if metric=='eligible' else 'unsupported'
        elif remaining<=EXPIRY_GUARD: value=None if metric.endswith('_ms') else 'UNVERIFIED' if metric=='geo_policy' else False if metric=='eligible' else 'stale'
        state[metric]=value
        d={'name':f"{row['tag']} {label}",'unique_id':uid,'default_entity_id':eid,'state_topic':topic,'value_template':'{{ value_json.'+metric+' }}','expire_after':max(1,remaining-EXPIRY_GUARD),'json_attributes_topic':topic,'json_attributes_template':'{{ {"node_id": value_json.node_id, "metric": "'+metric+'"} | to_json }}'}
        if metric.endswith('_ms'): d['unit_of_measurement']='ms'
        discovery.append((DISCOVERY+uid+'/config',d,True))
    return discovery,(topic,state,False)


def aggregate(data,shadow=True):
    topic=SHADOW+'aggregate' if shadow else PREFIX+'dynamic_rc2'
    uid=SHADOW_UID+'aggregate' if shadow else 'keenetic6059_dynamic_rc2'
    eid='sensor.keenetic_dynamic_vpn_rc2_mixed_shadow' if shadow else 'sensor.keenetic_dynamic_vpn_rc2'
    d={'name':'Keenetic mixed RC2 shadow' if shadow else 'Keenetic dynamic VPN RC2','unique_id':uid,'default_entity_id':eid,'state_topic':topic,'value_template':'{{ value_json.inventory_status }}','json_attributes_topic':topic,'expire_after':150}
    return [(DISCOVERY+uid+'/config',d,True),(topic,data,False)]


def publication(data,now,shadow=True,include_history=True):
    disc,state=[],[]
    if include_history:
        for row in data['rows']:
            d,s=history(row,now,shadow);disc.extend(d);state.append(s)
    a=aggregate(data,shadow);return [a[0]]+disc,[a[1]]+state


def field(s):
    b=s.encode();return struct.pack('!H',len(b))+b

def packet(kind,b):
    n=len(b);r=bytearray()
    while True:
        x=n%128;n//=128;r.append(x|(128 if n else 0))
        if not n:return bytes([kind])+bytes(r)+b


class ShadowMQTT:
    """Single QoS1 session, strict loopback-only broker; no production topics."""
    def __init__(self,host,port,deadline,mono=time.monotonic):
        if host not in ('127.0.0.1','::1'): raise PermissionError('shadow broker must be loopback')
        self.deadline=deadline;self.mono=mono;self.sock=socket.create_connection((host,port),timeout=self.timeout());self.pid=0
        try:
            self.send(packet(0x10,field('MQTT')+b'\x04\x02\x00\x14'+field('rc2-mixed-shadow-lab')))
            if self.recv(4)!=b'\x20\x02\x00\x00':raise RuntimeError('CONNECT refused')
        except BaseException:self.sock.close();raise
    def timeout(self):
        left=self.deadline-self.mono()
        if left<=0:raise Deadline('MQTT deadline')
        return min(5,left)
    def send(self,b):self.sock.settimeout(self.timeout());self.sock.sendall(b)
    def recv(self,n):
        b=b''
        while len(b)<n:
            self.sock.settimeout(self.timeout());p=self.sock.recv(n-len(b))
            if not p:raise ConnectionError('broker closed')
            b+=p
        return b
    def publish(self,topic,data,retain):
        if not (topic.startswith(SHADOW) or (topic.startswith(DISCOVERY+SHADOW_UID) and topic.endswith('/config'))) or any(c in topic for c in '+#\x00'):raise PermissionError('non-shadow topic')
        if retain != topic.startswith(DISCOVERY):raise ValueError('retain discovery only')
        b=encoded(data)
        if len(b)>(32768 if topic==SHADOW+'aggregate' else 4096):raise ValueError('MQTT payload too large')
        self.pid=self.pid%65535+1;pid=struct.pack('!H',self.pid)
        self.send(packet(0x33 if retain else 0x32,field(topic)+pid+b))
        if self.recv(4)!=b'\x40\x02'+pid:raise RuntimeError('PUBACK missing')
    def close(self):
        try:self.send(b'\xe0\x00')
        finally:self.sock.close()
    def __enter__(self):return self
    def __exit__(self,typ,val,tb):
        if typ:self.sock.close()
        else:self.close()


def publish_shadow(store, *, active_reader, pending_reader, inventory, broker_port, include_history=False, clock=time.time, mono=time.monotonic, sleep=time.sleep, deadline=None):
    """Separate history-on-probe / minute aggregate paths; no live MQTT credentials."""
    with store.lock('publish'):
        bundle=store.read();active=safe_pool(active_reader,inventory);pending=safe_pool(pending_reader,inventory,True)
        now=int(clock());data=render(bundle,active,pending,now)
        budget=HISTORY_BUDGET if include_history else 10
        limit=min(mono()+budget,deadline) if deadline is not None else mono()+budget
        with ShadowMQTT('127.0.0.1',broker_port,limit,mono) as m:
            d,_=publication(data,now,True,include_history)
            for msg in d:m.publish(*msg)
            if include_history:
                if mono()+SETTLE>=limit: raise Deadline('discovery settle deadline')
                sleep(SETTLE)
            # Never mix rows from a different state generation in one history batch.
            now=int(clock());data=render(bundle,safe_pool(active_reader,inventory),safe_pool(pending_reader,inventory,True),now)
            _,states=publication(data,now,True,include_history)
            for msg in states:m.publish(*msg)
        return data['count']


def scheduled_shadow(store, *, fetch, converter, inventory, probe, cleanup_error, verify, idle, active_reader, pending_reader, broker_port, clock=time.time, mono=time.monotonic, sleep=time.sleep, minute=None):
    """Combined scheduled probe + history run, capped before next 15-minute slot.
    Publication can fail independently without corrupting the committed generation.
    """
    # :03/:18/:33/:48 slot, with 15 s reserved before the next slot.
    # Reject a late start rather than start work that can cross the boundary.
    wall=clock();slot=int((wall-180)//900)*900+180
    remaining=slot+900-15-wall
    if not 0<=wall-slot<=CYCLE_BUDGET-(FETCH_BUDGET+PROBE_BUDGET+HISTORY_BUDGET) or remaining<FETCH_BUDGET+PROBE_BUDGET+HISTORY_BUDGET:
        raise Busy('late scheduled start')
    end=mono()+min(CYCLE_BUDGET,remaining)
    with store.lock('schedule'):
        current=store.read()
        if current and current.get('subscription_at',0)>=slot: raise Busy('slot already committed')
        token=probe_cycle(store,fetch=fetch,converter=converter,inventory=inventory,probe=probe,cleanup_error=cleanup_error,verify=verify,idle=idle,clock=clock,mono=mono,minute=minute)
        count=publish_shadow(store,active_reader=active_reader,pending_reader=pending_reader,inventory=inventory,broker_port=broker_port,include_history=True,clock=clock,mono=mono,sleep=sleep,deadline=end)
        return token,count


@contextlib.contextmanager
def pinned_converter(base,expected):
    """Reviewed converter only, fresh process required. Never invoke updater main.
    Supply exact reviewed pins, not hashes learned from unreviewed live sources.
    """
    from monitoring.full_subscription_snapshot import verify_sources,SOURCE_NAMES
    base=Path(base).resolve();verify_sources(base,expected)
    names=('setup_xray','xray_server_check','xray_openai_probe')
    if any(n in sys.modules for n in names):raise ValueError('unexpected preloaded source')
    oldpath=sys.path[:];sys.path.insert(0,str(base))
    try:
        m=runpy.run_path(str(base/SOURCE_NAMES[0]),run_name='__rc2_mixed_shadow__')
        converter=m['create_outbound']
        if Path(converter.__code__.co_filename).resolve()!=base/'setup_xray.py':raise ValueError('converter origin mismatch')
        verify_sources(base,expected)
        yield converter,lambda:verify_sources(base,expected)
        verify_sources(base,expected)
    finally:
        sys.path[:]=oldpath
        for name in names:sys.modules.pop(name,None)


def wired_probe_cycle(store, *, fetch, converter, verify, idle, **kw):
    """Repository adapters; explicit injected provider and verifier. No CLI/deploy."""
    from monitoring.vpn_inventory import inventory
    from monitoring.rc2_probe import probe_node
    from monitoring.isolated_pair_probe import CleanupError
    return probe_cycle(store,fetch=fetch,converter=converter,inventory=inventory,probe=probe_node,cleanup_error=CleanupError,verify=verify,idle=idle,**kw)
