"""One scheduler tick: persistent state and encrypted retry spool. Candidate only."""
import fcntl, hashlib, json, os, pathlib, tempfile, time
from scheduler import observe, acknowledge
from snapshot import archive
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
        p=root/name
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

def tick(work, root, entries, master, url, now=None, send=upload):
    work=pathlib.Path(work); work.mkdir(mode=0o700,parents=True,exist_ok=True)
    if work.is_symlink() or work.stat().st_mode & 0o077: raise ValueError('insecure state directory')
    statefile=work/'state.json'; spool=work/'pending.gcm'
    with (work/'lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        s=json.loads(statefile.read_text()) if statefile.exists() else {}
        now=time.time() if now is None else now
        def save(): atomic(statefile,json.dumps(s,sort_keys=True).encode())
        if 'pending' not in s:
            digest=fingerprint(root,entries)
            previous=s
            s,due=observe(s,digest,now)
            if s!=previous: save()
            if not due: return 'idle'
            data=archive(root,entries)
            # A live SQLite database may keep changing. Acknowledge only the pre-snapshot
            # observation; the next tick detects later changes rather than starving backup.
            blob=encrypt_archive(master,data); atomic(spool,blob)
            s['pending']={'source':digest,'sha256':hashlib.sha256(blob).hexdigest()}; save()
        blob=spool.read_bytes(); pending=s['pending']
        if hashlib.sha256(blob).hexdigest()!=pending['sha256']: raise ValueError('spool integrity')
        if send(url,master,blob)!=pending['sha256']: raise ValueError('receipt mismatch')
        s=acknowledge(s,pending['source']); save(); spool.unlink()
        return 'accepted'
