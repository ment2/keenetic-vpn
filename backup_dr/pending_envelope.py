"""Authenticated local pending envelope; no network or production operations."""
import hashlib, hmac, json, os, pathlib, re, stat, struct
from resource_guard import CIPHER_MAX

MAGIC=b'KBDRENV1'
HEADER_MAX=1024
LIMIT=len(MAGIC)+4+HEADER_MAX+CIPHER_MAX+32
HEX=re.compile(r'[0-9a-f]{64}\Z')

def valid_digest(x): return isinstance(x,str) and HEX.fullmatch(x) is not None

def canonical(x): return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii')

def mac(master):
    if len(master)!=32: raise ValueError('key length')
    key=hmac.digest(master,b'keenetic-backup-dr/pending-envelope/v1','sha256')
    return hmac.new(key,digestmod='sha256')

def sync_dir(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try: os.fsync(fd)
    finally: os.close(fd)

def write(path,master,config,source,blob):
    """Exclusive named staging file, fsync before atomic publication.
    Caller holds the state lock. On any failure leave evidence intact.
    """
    path=pathlib.Path(path); stage=path.with_name(path.name+'.tmp')
    if os.path.lexists(path): raise ValueError('pending envelope already exists')
    if not valid_digest(config) or not valid_digest(source) or not 28<=len(blob)<=CIPHER_MAX: raise ValueError('invalid envelope input')
    meta={'version':1,'config':config,'source':source,'sha256':hashlib.sha256(blob).hexdigest(),'size':len(blob)}
    header=canonical(meta); prefix=MAGIC+struct.pack('>I',len(header))+header
    m=mac(master); m.update(prefix); m.update(blob)
    fd=os.open(stage,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as f:
        f.write(prefix); f.write(blob); f.write(m.digest()); f.flush(); os.fsync(f.fileno())
    os.replace(stage,path); sync_dir(path.parent)
    return meta

def read(path,master,config,*,sync=False):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as f:
        s=os.fstat(f.fileno())
        if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1 or s.st_uid!=os.geteuid() or s.st_mode&0o077 or s.st_size>LIMIT: raise ValueError('unsafe envelope')
        prefix=f.read(len(MAGIC)+4)
        if len(prefix)!=len(MAGIC)+4 or not prefix.startswith(MAGIC): raise ValueError('envelope header')
        n=struct.unpack('>I',prefix[-4:])[0]
        if not 1<=n<=HEADER_MAX: raise ValueError('envelope header size')
        raw=f.read(n)
        try: meta=json.loads(raw)
        except (ValueError,UnicodeError,RecursionError): raise ValueError('envelope metadata') from None
        if not isinstance(meta,dict) or set(meta)!={'version','config','source','sha256','size'} or type(meta['version']) is not int or meta['version']!=1 or not all(valid_digest(meta[k]) for k in ('config','source','sha256')) or type(meta['size']) is not int or not 28<=meta['size']<=CIPHER_MAX or raw!=canonical(meta): raise ValueError('envelope metadata')
        if meta['config']!=config: raise ValueError('envelope configuration mismatch')
        if s.st_size!=len(prefix)+n+meta['size']+32: raise ValueError('envelope size')
        blob=f.read(meta['size']); tag=f.read(32)
        m=mac(master); m.update(prefix); m.update(raw); m.update(blob)
        if len(blob)!=meta['size'] or len(tag)!=32 or f.read(1) or not hmac.compare_digest(m.digest(),tag) or hashlib.sha256(blob).hexdigest()!=meta['sha256']: raise ValueError('envelope integrity')
        if sync: os.fsync(f.fileno())
        return meta,blob

def recover(path,master,config):
    """Promote a complete authenticated staging file. Partial staging blocks.
    No archive can have been sent until the final name is durable.
    """
    path=pathlib.Path(path); stage=path.with_name(path.name+'.tmp')
    if os.path.lexists(stage):
        if os.path.lexists(path): raise ValueError('conflicting envelope staging')
        meta,blob=read(stage,master,config,sync=True)
        os.replace(stage,path); sync_dir(path.parent)
        return meta,blob
    if os.path.lexists(path):
        # Also fence a prior rename whose directory fsync did not complete.
        meta,blob=read(path,master,config,sync=True); sync_dir(path.parent)
        return meta,blob
    return None
