"""Bounded manifest verification and isolated restore for regular-file archives."""
import hashlib, io, json, pathlib, tarfile, os, stat, tempfile
MAX = 48*1024*1024
MAX_FILES = 4096
MANIFEST = '.backup-manifest-v1.json'

def valid_name(name):
    p=pathlib.PurePosixPath(name)
    if not name or p.is_absolute() or '..' in p.parts or name!=str(p) or name in ('.', MANIFEST) or '\\' in name:
        raise ValueError('invalid member name')
    return p

def describe(info,data,kind):
    return dict(name=info.name,size=len(data),sha256=hashlib.sha256(data).hexdigest(),kind=kind,mode=info.mode,uid=info.uid,gid=info.gid,mtime=info.mtime)

def verify(data, expected=None):
    found={}; total=0; raw=None
    with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as t:
        for member in t:
            if not member.isfile() or member.size<0 or member.size>MAX: raise ValueError('invalid archive member')
            if member.name==MANIFEST:
                if raw is not None or member.size>1024*1024: raise ValueError('manifest limit')
                raw=t.extractfile(member).read(); continue
            valid_name(member.name)
            if member.name in found or len(found)>=MAX_FILES: raise ValueError('duplicate or too many members')
            total+=member.size
            if total>MAX: raise ValueError('archive limit')
            content=t.extractfile(member).read()
            if len(content)!=member.size: raise ValueError('truncated member')
            found[member.name]=(member,content)
    if raw is None: raise ValueError('manifest missing')
    m=json.loads(raw)
    if not isinstance(m,dict) or m.get('version')!=1 or not isinstance(m.get('entries'),list) or len(m['entries'])!=len(found): raise ValueError('manifest schema')
    names=set()
    for e in m['entries']:
        if not isinstance(e,dict) or e.get('kind') not in ('file','sqlite') or e.get('name') not in found or e['name'] in names: raise ValueError('manifest entry')
        names.add(e['name']); member,content=found[e['name']]
        if e!=describe(member,content,e['kind']): raise ValueError('manifest mismatch')
    if expected is not None and {(e['name'],e['kind']) for e in m['entries']} != {tuple(e) for e in expected}:
        raise ValueError('unexpected group members')
    for name in names:
        if any(str(p) in names for p in pathlib.PurePosixPath(name).parents): raise ValueError('path collision')
    return found

def restore(data,parent):
    found=verify(data)
    root=pathlib.Path(tempfile.mkdtemp(prefix='restore-',dir=parent))
    for name,(info,content) in found.items():
        p=root/name; p.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as f: f.write(content); f.flush(); os.fsync(f.fileno())
    # Deliberately do not activate executables or restore ownership into production.
    return root
