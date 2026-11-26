"""Local authenticated generation gate; explicit offline transitions only.
This is not a distributed transaction. Both services must be stopped before a
coordinated transition. Never infer permission to change from a new plan file.
"""
import contextlib, fcntl, hashlib, hmac, json, os, pathlib, re, stat
from groups import validate, config_id, GROUP
from pending_envelope import canonical, valid_digest
from runtime import atomic, private_bytes

NAME='.group-config.json'
LIMIT=65536


def mapping(config): return {g:config_id(e) for g,e in validate(config).items()}


def _sign(master,role,record):
    if len(master)!=32 or role not in ('sender','receiver'): raise ValueError('registry identity')
    key=hmac.digest(master,b'keenetic-backup-dr/config-registry/v1/'+role.encode(),'sha256')
    return hmac.digest(key,canonical(record),'sha256').hex()


def _root(root):
    root=pathlib.Path(root); s=root.lstat()
    if not stat.S_ISDIR(s.st_mode) or s.st_mode&0o077 or s.st_uid!=os.geteuid(): raise ValueError('insecure registry root')
    return root


def _map_ok(m): return isinstance(m,dict) and bool(m) and all(isinstance(g,str) and GROUP.fullmatch(g) and valid_digest(v) for g,v in m.items())


def read(root,master,role):
    root=_root(root); p=root/NAME
    if not os.path.lexists(p): return None
    raw=private_bytes(p,LIMIT); d=json.loads(raw)
    if not isinstance(d,dict) or set(d)!={'record','mac'} or not isinstance(d['record'],dict): raise ValueError('invalid group registry')
    r=d['record']
    if set(r)!={'version','active','retired'} or type(r['version']) is not int or r['version']!=1 or not _map_ok(r['active']) or not isinstance(r['retired'],dict) or any(not isinstance(g,str) or not GROUP.fullmatch(g) or not isinstance(v,list) or not v or not all(valid_digest(x) for x in v) or v!=sorted(set(v)) for g,v in r['retired'].items()): raise ValueError('invalid group registry')
    if not valid_digest(d['mac']) or not hmac.compare_digest(d['mac'],_sign(master,role,r)) or raw!=canonical(d): raise ValueError('group registry integrity')
    return r


def _save(root,master,role,r):
    raw=canonical({'record':r,'mac':_sign(master,role,r)})
    if len(raw)>LIMIT: raise ValueError('group registry limit')
    atomic(root/NAME,raw)


def _state_dirs(root):
    """Only expected group/generation directories; refuse links and unknown dirs."""
    for g in root.iterdir():
        if g.is_symlink(): raise ValueError('unsafe sender directory')
        if not g.is_dir(): continue
        if not GROUP.fullmatch(g.name): raise ValueError('unknown sender directory')
        _root(g)
        for p in g.iterdir():
            if p.is_symlink() or not p.is_dir() or not valid_digest(p.name): raise ValueError('unknown sender generation')
            _root(p)
            yield g.name,p


def _pending(p):
    if any(os.path.lexists(p/n) for n in ('pending.gcm','pending.envelope','pending.envelope.tmp')): return True
    if any(x.name.startswith('.pending-') for x in p.iterdir()): return True
    s=p/'state.json'
    if not os.path.lexists(s): return False
    d=json.loads(private_bytes(s,16384))
    if not isinstance(d,dict): raise ValueError('invalid state schema')
    return 'pending' in d


def ensure(root,master,role,config):
    """Caller holds role lock. Initial legacy adoption is conservative."""
    root=_root(root); current=mapping(config); r=read(root,master,role)
    if r is None:
        if role=='sender':
            for g,p in _state_dirs(root):
                if current.get(g)!=p.name: raise ValueError('unregistered historical sender generation')
        r={'version':1,'active':current,'retired':{}}
        _save(root,master,role,r)
    elif r['active']!=current: raise ValueError('group change requires coordinated approval')
    if role=='sender':
        for g,p in _state_dirs(root):
            if current.get(g)!=p.name:
                if p.name not in r['retired'].get(g,[]): raise ValueError('unregistered historical sender generation')
                if _pending(p): raise ValueError('retired generation contains pending work')
    return r


@contextlib.contextmanager
def exclusive(path):
    fd=os.open(path,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        s=os.fstat(fd)
        if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.geteuid() or s.st_mode&0o077 or s.st_nlink!=1: raise ValueError('unsafe registry lock')
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        yield
    finally: os.close(fd)


def approve_change(root,master,role,old,new,*,coordinated=False):
    """Local owner-only maintenance helper, not called from scheduled tick.
    Caller must independently fence both services and drain sender under old
    plan; receiver cannot prove remote sender state. Never changes archives.
    """
    if coordinated is not True: raise ValueError('explicit coordinated maintenance required')
    root=_root(root); previous=mapping(old); target=mapping(new)
    if previous==target: raise ValueError('no group change')
    if role not in ('sender','receiver'): raise ValueError('registry role')
    with exclusive(root/'service.lock'), exclusive(root/('groups.lock' if role=='sender' else '.quota.lock')):
        r=read(root,master,role)
        if r is None or r['active']!=previous: raise ValueError('old group configuration mismatch')
        if role=='sender':
            for g,p in _state_dirs(root):
                if previous.get(g)!=p.name and p.name not in r['retired'].get(g,[]): raise ValueError('unknown historical sender generation')
                # State lock also fences a direct tick cooperating with registry.
                with exclusive(p/'lock'):
                    if _pending(p): raise ValueError('pending work must be drained before group change')
        retired={g:list(v) for g,v in r['retired'].items()}
        for g,c in previous.items():
            if target.get(g)!=c: retired[g]=sorted(set(retired.get(g,[])+[c]))
        _save(root,master,role,{'version':1,'active':target,'retired':retired})
