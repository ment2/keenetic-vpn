"""HA receiver heartbeat; status never includes private data or keys."""
import json, os, pathlib, re, shutil, tempfile, time

def status(root,now=None,reserve=5*1024**3):
    root=pathlib.Path(root); now=time.time() if now is None else now
    files=[p.stat() for p in root.iterdir() if re.fullmatch(r'[0-9a-f]{64}\.gcm',p.name) and not p.is_symlink() and p.is_file()]
    free=shutil.disk_usage(root).free
    return {'version':1,'receiver_heartbeat':int(now),'status':'low_space' if free<reserve else ('ready' if files else 'awaiting_first_backup'),'archive_count':len(files),'archive_bytes':sum(s.st_size for s in files),'latest_archive_mtime':int(max(s.st_mtime for s in files)) if files else None,'free_bytes':free}

def publish(path,record):
    path=pathlib.Path(path); fd,tmp=tempfile.mkstemp(prefix='.backup-status-',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as f: json.dump(record,f,sort_keys=True); f.flush(); os.fsync(f.fileno()); os.fchmod(f.fileno(),0o644)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def run(server,root,path,interval=30):
    server.timeout=interval
    try:
        while True:
            publish(path,status(root)); server.handle_request()
    finally: server.server_close()
