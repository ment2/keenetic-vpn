"""Bounded, authenticated sender heartbeat; no archive contents or local paths."""
import hashlib,hmac,json,time,pathlib,os,stat
from transport import keys,encrypt_archive,upload,receipt
from crypto import open_sealed
from runtime import atomic
from groups import validate

PATH='/v1/sender-status'
MAX_BODY=8192
STALE=900
FUTURE=60
RESULTS={'idle','accepted','preflight_failed','retry_required'}

def status_key(master):
    if len(master)!=32: raise ValueError('key length')
    return hmac.digest(master,b'keenetic-backup-v1/sender-status','sha256')

def report(results,now=None):
    return {'version':1,'heartbeat':int(time.time() if now is None else now),'groups':results}

def validate_report(record,groups,now):
    if not isinstance(record,dict) or set(record)!={'version','heartbeat','groups'} or type(record['version']) is not int or record['version']!=1: raise ValueError('status schema')
    t=record['heartbeat']; rows=record['groups']
    if type(t) is not int or t<=0 or not now-STALE<=t<=now+FUTURE: raise ValueError('status timestamp')
    if not isinstance(rows,dict) or set(rows)!=groups or any(type(v) is not str or v not in RESULTS for v in rows.values()): raise ValueError('status groups')
    return record

class Inbox:
    def __init__(self,path,master,config,clock=time.time):
        self.path=pathlib.Path(path); self.key=status_key(master); self.groups=set(validate(config)); self.clock=clock
        p=self.path.parent; s=p.lstat()
        if p.resolve()!=p.absolute() or not stat.S_ISDIR(s.st_mode) or s.st_mode&0o077 or s.st_uid!=os.geteuid(): raise ValueError('private sender state directory required')
    def read(self):
        try: fd=os.open(self.path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        except FileNotFoundError: return None
        with os.fdopen(fd,'rb') as f:
            s=os.fstat(f.fileno())
            if not stat.S_ISREG(s.st_mode) or s.st_mode&0o077 or s.st_uid!=os.geteuid() or s.st_size>MAX_BODY: raise ValueError('invalid sender state')
            blob=f.read(MAX_BODY+1)
        record=json.loads(open_sealed(keys(self.key)[0],blob))
        # Old, authenticated records remain available for stale detection and replay rejection.
        return validate_report(record,self.groups,record['heartbeat'])
    def accept(self,blob):
        if not 28<=len(blob)<=MAX_BODY: raise ValueError('status size')
        r=validate_report(json.loads(open_sealed(keys(self.key)[0],blob)),self.groups,int(self.clock()))
        old=self.read()
        if old is not None and r['heartbeat']<=old['heartbeat']: raise ValueError('status replay')
        atomic(self.path,blob)
        return receipt(keys(self.key)[1],hashlib.sha256(blob).hexdigest()).encode('ascii')
    def summary(self):
        try: r=self.read()
        except (OSError,ValueError,TypeError,KeyError): return {'status':'invalid','heartbeat':None,'groups':{}}
        if r is None: return {'status':'missing','heartbeat':None,'groups':{}}
        now=int(self.clock()); t=r['heartbeat']
        state='stale' if now-t>STALE or t-now>FUTURE else 'ok' if all(x in ('idle','accepted') for x in r['groups'].values()) else 'retry_required'
        return {'status':state,'heartbeat':t,'groups':r['groups']}

def send_report(origin,master,results,now=None):
    key=status_key(master); data=json.dumps(report(results,now),sort_keys=True,separators=(',',':')).encode()
    blob=encrypt_archive(key,data)
    if len(blob)>MAX_BODY: raise ValueError('status size')
    return upload(origin.rstrip('/')+PATH,key,blob)
