"""Explicit allowlist only. SQLite snapshots remain in memory."""
import io, os, pathlib, sqlite3, tarfile, stat
MAX = 48*1024*1024

def sqlite_snapshot(path):
    source=sqlite3.connect(pathlib.Path(path).resolve().as_uri()+'?mode=ro',uri=True,timeout=5)
    dest=sqlite3.connect(':memory:')
    try:
        source.backup(dest)
        if dest.execute('PRAGMA quick_check').fetchone()!=('ok',): raise ValueError('SQLite integrity')
        return dest.serialize()
    finally: dest.close(); source.close()

def archive(root, entries):
    root=pathlib.Path(root).resolve(); buf=io.BytesIO(); seen=set(); total=0
    with tarfile.open(fileobj=buf,mode='w:gz') as tar:
        for name, kind in entries:
            rel=pathlib.PurePosixPath(name)
            if rel.is_absolute() or '..' in rel.parts or name in seen: raise ValueError('invalid path')
            seen.add(name); p=root/rel
            if p.resolve()!=p or not p.is_file(): raise ValueError('nonregular or symlink')
            before=p.stat()
            if before.st_size>MAX-total: raise ValueError('size limit')
            if kind=='sqlite': data=sqlite_snapshot(p)
            elif kind=='file':
                with p.open('rb') as f: data=f.read(MAX-total+1)
                after=p.stat()
                if (before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_ino,after.st_size,after.st_mtime_ns): raise ValueError('file changed')
            else: raise ValueError('unknown kind')
            total+=len(data)
            if total>MAX: raise ValueError('size limit')
            info=tarfile.TarInfo(name); info.size=len(data); info.mode=stat.S_IMODE(before.st_mode); info.uid=before.st_uid; info.gid=before.st_gid; info.mtime=int(before.st_mtime)
            tar.addfile(info,io.BytesIO(data))
    return buf.getvalue()
