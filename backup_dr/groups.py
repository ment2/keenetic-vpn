"""Explicit, stable group configuration; no wildcard secret discovery or silent truncation."""
import hashlib, hmac, json, pathlib, re, stat
from manifest import valid_name, MAX_FILES
from resource_guard import SOURCE_MAX

GROUP=re.compile(r'[a-z][a-z0-9-]{0,47}\Z')

def validate(config):
    if not isinstance(config,dict) or not config: raise ValueError('empty group configuration')
    out={}; seen=set()
    for group,entries in config.items():
        if not isinstance(group,str) or not GROUP.fullmatch(group): raise ValueError('invalid group id')
        if not isinstance(entries,list) or not 1<=len(entries)<=MAX_FILES: raise ValueError('invalid group entries')
        result=[]
        for entry in entries:
            if not isinstance(entry,(tuple,list)) or len(entry)!=2: raise ValueError('invalid entry')
            name,kind=entry
            if not isinstance(name,str) or '\x00' in name or kind not in ('file','sqlite'): raise ValueError('invalid entry')
            valid_name(name)
            if name in seen: raise ValueError('duplicate source across groups')
            seen.add(name); result.append((name,kind))
        out[group]=sorted(result)
    return out

def preflight(root,config,limit=SOURCE_MAX):
    """Size estimate only: actual SQLite page count/archives still checked by snapshot."""
    if not 0<limit<=SOURCE_MAX: raise ValueError('invalid budget')
    root=pathlib.Path(root).resolve(); config=validate(config); results={}
    for group,entries in config.items():
        size=0; oversized=0; missing=0; invalid=0
        for name,kind in entries:
            p=root/name
            try:
                st=p.lstat()
                if p.resolve()!=p or not stat.S_ISREG(st.st_mode): invalid+=1; continue
                n=st.st_size
                if kind=='sqlite':
                    wal=p.with_name(p.name+'-wal')
                    if wal.exists() or wal.is_symlink():
                        w=wal.lstat()
                        if wal.resolve()!=wal or not stat.S_ISREG(w.st_mode): invalid+=1; continue
                        n+=w.st_size
                size+=n; oversized+=int(n>limit)
            except FileNotFoundError: missing+=1
        results[group]={'entries':len(entries),'estimated_bytes':size,'oversized_files':oversized,'missing':missing,'invalid':invalid,'ready':not(missing or invalid or oversized or size>limit)}
    return results

def group_key(master,group):
    if len(master)!=32 or not GROUP.fullmatch(group): raise ValueError('invalid group key input')
    return hmac.digest(master,b'keenetic-backup-dr/group/v1/'+group.encode('ascii'),'sha256')

def config_id(entries):
    return hashlib.sha256(json.dumps(sorted(entries),separators=(',',':')).encode()).hexdigest()
