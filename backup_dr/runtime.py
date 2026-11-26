"""One scheduler tick: persistent state and encrypted retry spool. Candidate only."""
import fcntl, hashlib, json, os, pathlib, re, stat, tempfile, time
from scheduler import observe, acknowledge
from snapshot import archive
from manifest import valid_name
from resource_guard import check_memory, SOURCE_MAX, CIPHER_MAX
from transport import encrypt_archive, upload
from groups import config_id
import pending_envelope as envelope

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
    statefile=work/'state.json'; legacy=work/'pending.gcm'; spool=work/'pending.envelope'
    generation=config_id(entries)
    fd=os.open(work/'lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'a') as lock:
        st=os.fstat(lock.fileno())
        if not stat.S_ISREG(st.st_mode) or st.st_uid!=os.geteuid() or st.st_nlink!=1 or st.st_mode&0o077: raise ValueError('insecure state lock')
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        s=json.loads(private_bytes(statefile,16384)) if os.path.lexists(statefile) else {}
        if not isinstance(s,dict): raise ValueError('invalid state schema')
        now=time.time() if now is None else now
        def save(): atomic(statefile,json.dumps(s,sort_keys=True).encode())
        pending=s.get('pending'); has_pending='pending' in s
        if has_pending and (not isinstance(pending,dict) or set(pending) not in ({'source','sha256'},{'source','sha256','format'}) or not all(sha256_text(pending[k]) for k in ('source','sha256')) or ('format' in pending and pending['format']!='envelope-v1')): raise ValueError('invalid pending state')
        has_new=os.path.lexists(spool) or os.path.lexists(spool.with_name(spool.name+'.tmp'))
        has_old=os.path.lexists(legacy)
        if has_new and has_old: raise ValueError('conflicting pending formats')
        if has_pending and not (has_new or has_old): raise FileNotFoundError('pending archive missing')
        if has_new:
            if has_pending and pending.get('format')!='envelope-v1': raise ValueError('pending format mismatch')
            check_memory(); meta,blob=envelope.recover(spool,master,generation)
            recovered={'source':meta['source'],'sha256':meta['sha256'],'format':'envelope-v1'}
            if has_pending and pending!=recovered: raise ValueError('pending metadata mismatch')
            if not has_pending and s.get('accepted_spool')==meta['sha256'] and s.get('committed')==meta['source']:
                remove_spool(spool); has_new=False; del blob
            else:
                # Envelope is authoritative after crash between its commit and state marker.
                if not has_pending: s['pending']=recovered; save()
                pending=recovered
        if has_old:
            check_memory(); blob=private_bytes(legacy,CIPHER_MAX); digest=hashlib.sha256(blob).hexdigest()
            if not has_pending:
                if not sha256_text(s.get('committed')) or s.get('accepted_spool')!=digest: raise ValueError('untracked spool requires review')
                remove_spool(legacy); has_old=False; del blob
            elif pending.get('format') is not None or digest!=pending['sha256']: raise ValueError('spool integrity')
        if not (has_new or has_old):
            if source_ready is not None and not source_ready(): return 'preflight_failed'
            digest=fingerprint(root,entries)
            previous=s; s,due=observe(s,digest,now)
            if s!=previous: save()
            if not due: return 'idle'
            check_memory(); data=archive(root,entries,limit=SOURCE_MAX)
            if len(data)+28>CIPHER_MAX: raise ValueError('ciphertext budget')
            blob=encrypt_archive(master,data); del data
            meta=envelope.write(spool,master,generation,digest,blob)
            pending={'source':meta['source'],'sha256':meta['sha256'],'format':'envelope-v1'}
            s['pending']=pending; save(); has_new=True
        if send(url,master,blob)!=pending['sha256']: raise ValueError('receipt mismatch')
        s=acknowledge(s,pending['source']); s['accepted_spool']=pending['sha256']; save()
        remove_spool(spool if has_new else legacy)
        return 'accepted'
