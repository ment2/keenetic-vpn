"""One scheduler tick: persistent state and encrypted retry spool. Candidate only."""
import fcntl, hashlib, json, os, pathlib, re, stat, tempfile, time
from scheduler import observe, acknowledge
from snapshot import archive
from manifest import valid_name
from resource_guard import check_memory, SOURCE_MAX, CIPHER_MAX
from transport import encrypt_archive, upload

def atomic(path, data):
    path=pathlib.Path(path); fd,tmp=tempfile.mkstemp(prefix='.pending-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f: f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,path)
        dfd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try: os.fsync(dfd)
        finally: os.close(dfd)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def fingerprint(root, entries):
    root=pathlib.Path(root).resolve(); h=hashlib.sha256()
    for name,kind in sorted(entries):
        p=root/valid_name(name)
        if p.resolve()!=p or not p.is_file(): raise ValueError('invalid source')
        # Hash ordinary source contents, not atime. SQLite main/WAL metadata catches commits.
        for item in ([p,p.with_name(p.name+'-wal')] if kind=='sqlite' else [p]):
            h.update(str(item.relative_to(root)).encode()+b'\0')
            try:
                st=item.stat()
                if item.resolve()!=item or not item.is_file(): raise ValueError('invalid source')
                h.update(str((st.st_size,st.st_mtime_ns,st.st_ino,st.st_mode,st.st_uid,st.st_gid)).encode()+b'\0')
                if kind!='sqlite':
                    with item.open('rb') as f:
                        for chunk in iter(lambda:f.read(65536),b''): h.update(chunk)
            except FileNotFoundError:
                if item==p: raise
                h.update(b'absent')
    return h.hexdigest()

def private_bytes(path, limit):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        st=os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid!=os.geteuid() or st.st_mode&0o077 or st.st_nlink!=1 or st.st_size>limit:
            raise ValueError('insecure or oversized state file')
        with os.fdopen(fd,'rb') as f:
            fd=-1; data=f.read(limit+1)
        if len(data)>limit: raise ValueError('state file size')
        return data
    finally:
        if fd>=0: os.close(fd)

def sha256_text(value):
    return isinstance(value,str) and re.fullmatch(r'[0-9a-f]{64}',value) is not None

def remove_spool(path):
    path.unlink()
    fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try: os.fsync(fd)
    finally: os.close(fd)

def tick(work, root, entries, master, url, now=None, send=upload, *, source_ready=None):
    work=pathlib.Path(work); work.mkdir(mode=0o700,parents=True,exist_ok=True)
    if work.is_symlink() or work.stat().st_uid!=os.geteuid() or work.stat().st_mode & 0o077: raise ValueError('insecure state directory')
    statefile=work/'state.json'; spool=work/'pending.gcm'
    with (work/'lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        s=json.loads(private_bytes(statefile,16384)) if os.path.lexists(statefile) else {}
        if not isinstance(s,dict): raise ValueError('invalid state schema')
        now=time.time() if now is None else now
        def save(): atomic(statefile,json.dumps(s,sort_keys=True).encode())
        if 'pending' not in s:
            # A crash after acknowledged state was saved may leave the exact
            # accepted ciphertext behind. Only that explicitly recorded digest
            # permits cleanup; never overwrite an untracked pending archive.
            if os.path.lexists(spool):
                check_memory()
                if not sha256_text(s.get('accepted_spool')) or not sha256_text(s.get('committed')) or hashlib.sha256(private_bytes(spool,CIPHER_MAX)).hexdigest()!=s['accepted_spool']:
                    raise ValueError('untracked spool requires review')
                remove_spool(spool)
            if source_ready is not None and not source_ready(): return 'preflight_failed'
            digest=fingerprint(root,entries)
            previous=s
            s,due=observe(s,digest,now)
            if s!=previous: save()
            if not due: return 'idle'
            check_memory()
            data=archive(root,entries,limit=SOURCE_MAX)
            if len(data)+28>CIPHER_MAX: raise ValueError('ciphertext budget')
            # A live SQLite database may keep changing. Acknowledge only the pre-snapshot
            # observation; the next tick detects later changes rather than starving backup.
            blob=encrypt_archive(master,data); atomic(spool,blob)
            s['pending']={'source':digest,'sha256':hashlib.sha256(blob).hexdigest()}; save()
        check_memory()
        pending=s['pending']
        if not isinstance(pending,dict) or set(pending)!={'source','sha256'} or not all(sha256_text(pending[k]) for k in ('source','sha256')):
            raise ValueError('invalid pending state')
        blob=private_bytes(spool,CIPHER_MAX)
        if hashlib.sha256(blob).hexdigest()!=pending['sha256']: raise ValueError('spool integrity')
        if send(url,master,blob)!=pending['sha256']: raise ValueError('receipt mismatch')
        s=acknowledge(s,pending['source']); s['accepted_spool']=pending['sha256']; save(); remove_spool(spool)
        return 'accepted'
