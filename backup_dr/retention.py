"""Explicit retention maintenance, never remove unverified or newest archives."""
import hashlib, os, pathlib, re, time
from crypto import open_sealed
from transport import keys, LIMIT

def prune(root, master, now=None, days=30, keep=2, *, require_manifest=False):
    if days<1 or keep<2: raise ValueError('unsafe retention')
    now=time.time() if now is None else now
    root=pathlib.Path(root); candidates=[]
    for p in root.iterdir():
        if not re.fullmatch(r'[0-9a-f]{64}\.gcm',p.name) or p.is_symlink() or not p.is_file(): continue
        st=p.stat()
        if st.st_size>LIMIT: continue
        blob=p.read_bytes()
        if hashlib.sha256(blob).hexdigest()!=p.stem: continue
        try:
            data=open_sealed(keys(master)[0],blob)
            if require_manifest:
                from manifest import verify
                verify(data)
        except (ValueError, OSError, EOFError, TypeError, KeyError, AttributeError, __import__('tarfile').TarError): continue
        candidates.append((st.st_mtime,p))
    candidates.sort(reverse=True)
    deleted=[]
    for mtime,p in candidates[keep:]:
        if now-mtime>=days*86400:
            p.unlink(); deleted.append(p.name)
    if deleted:
        fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)
    return deleted
