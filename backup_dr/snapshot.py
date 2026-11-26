"""Explicit allowlist only. SQLite snapshots remain in memory."""
import io, os, pathlib, sqlite3, tarfile, stat, time
from manifest import MAX, MAX_FILES, MANIFEST, valid_name, describe
import json

def sqlite_snapshot(path, limit=MAX, timeout=30):
    source=sqlite3.connect(pathlib.Path(path).resolve().as_uri()+'?mode=ro',uri=True,timeout=5)
    dest=sqlite3.connect(':memory:')
    try:
        deadline=time.monotonic()+timeout
        page_size=source.execute('PRAGMA page_size').fetchone()[0]
        def progress(status,remaining,total):
            if total*page_size>limit: raise ValueError('SQLite size limit')
            if time.monotonic()>deadline: raise TimeoutError('SQLite backup deadline')
        source.backup(dest,pages=64,progress=progress,sleep=0.05)
        if dest.execute('PRAGMA quick_check').fetchone()!=('ok',): raise ValueError('SQLite integrity')
        return dest.serialize()
    finally: dest.close(); source.close()

def archive(root, entries, limit=MAX):
    if not 0<limit<=MAX: raise ValueError('invalid source budget')
    root=pathlib.Path(root).resolve(); buf=io.BytesIO(); seen=set(); total=0; records=[]
    with tarfile.open(fileobj=buf,mode='w:gz') as tar:
        for name, kind in entries:
            rel=valid_name(name)
            if name in seen or len(seen)>=MAX_FILES: raise ValueError('invalid path')
            seen.add(name); p=root/rel
            if p.resolve()!=p or not p.is_file(): raise ValueError('nonregular or symlink')
            before=p.stat()
            if before.st_size>limit-total: raise ValueError('size limit')
            if kind=='sqlite': data=sqlite_snapshot(p,limit-total)
            elif kind=='file':
                with p.open('rb') as f: data=f.read(limit-total+1)
                after=p.stat()
                if (before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_ino,after.st_size,after.st_mtime_ns): raise ValueError('file changed')
            else: raise ValueError('unknown kind')
            total+=len(data)
            if total>limit: raise ValueError('size limit')
            info=tarfile.TarInfo(name); info.size=len(data); info.mode=stat.S_IMODE(before.st_mode); info.uid=before.st_uid; info.gid=before.st_gid; info.mtime=int(before.st_mtime)
            tar.addfile(info,io.BytesIO(data)); records.append(describe(info,data,kind))
        raw=json.dumps(dict(version=1,entries=records),sort_keys=True,separators=(',',':')).encode()
        if len(raw)>1024*1024: raise ValueError('manifest limit')
        info=tarfile.TarInfo(MANIFEST); info.size=len(raw); info.mode=0o600; tar.addfile(info,io.BytesIO(raw))
    return buf.getvalue()
