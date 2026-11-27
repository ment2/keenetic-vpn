"""Disposable journal experiment only. Never use on a router or real sources."""
import hashlib
import json
import os
import signal
from pathlib import Path
import tempfile

NAMES=("updater","pins")
OLD={"updater":b"old fixture\n","pins":b"old pins fixture\n"}
NEW={"updater":b"new fixture\n","pins":b"new pins fixture\n"}

def digest(b): return hashlib.sha256(b).hexdigest()

def sync_dir(p):
    fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)

def atomic(p,b):
    fd,name=tempfile.mkstemp(prefix=".fixture-",dir=p.parent)
    try:
        with os.fdopen(fd,"wb") as f:
            f.write(b); f.flush(); os.fsync(f.fileno())
        os.replace(name,p);sync_dir(p.parent)
    finally:
        if os.path.exists(name): os.unlink(name)

def check_root(root):
    root=Path(root).resolve()
    if not root.name.startswith("v23-journal-fixture-") or root.parent!=Path(tempfile.gettempdir()).resolve():
        raise ValueError("disposable fixture directory required")
    if (root/"marker").read_bytes()!=b"synthetic-only":
        raise ValueError("missing fixture marker")
    return root

def cut(stage,wanted):
    if stage==wanted: os.kill(os.getpid(),signal.SIGKILL)

def journal(root,state):
    atomic(root/"journal",json.dumps({"state":state,"old":{k:digest(v) for k,v in OLD.items()},"new":{k:digest(v) for k,v in NEW.items()}},sort_keys=True).encode())

def start(root,crash=None):
    root=check_root(root)
    if (root/"journal").exists() or any((root/k).read_bytes()!=OLD[k] for k in NAMES):
        raise RuntimeError("CAS mismatch")
    for k in NAMES: atomic(root/(k+".backup"),OLD[k])
    journal(root,"prepared");cut("prepared",crash)
    for k in ("pins","updater"):
        if (root/k).read_bytes()!=OLD[k]: raise RuntimeError("CAS mismatch")
        atomic(root/k,NEW[k]);cut(k,crash)
    if any((root/k).read_bytes()!=NEW[k] for k in NAMES): raise RuntimeError("pair mismatch")
    journal(root,"committed");cut("committed",crash)

def recover(root,crash=None):
    root=check_root(root)
    p=root/"journal"
    if not p.exists(): return "no transaction"
    data=json.loads(p.read_bytes())
    if data["state"] not in ("prepared","committed"): raise RuntimeError("journal invalid")
    if data["old"]!={k:digest(v) for k,v in OLD.items()} or data["new"]!={k:digest(v) for k,v in NEW.items()}: raise RuntimeError("journal hashes invalid")
    # Inspect all objects and backups before writing any file.
    for k in NAMES:
        if (root/k).read_bytes() not in (OLD[k],NEW[k]) or (root/(k+".backup")).read_bytes()!=OLD[k]:
            raise RuntimeError("unknown generation or corrupt backup")
    if data["state"]=="committed":
        if any((root/k).read_bytes()!=NEW[k] for k in NAMES): raise RuntimeError("committed pair mismatch")
        return "committed"
    for k in ("updater","pins"):
        if (root/k).read_bytes()==NEW[k]: atomic(root/k,OLD[k])
        cut("restore-"+k,crash)
    if any((root/k).read_bytes()!=OLD[k] for k in NAMES): raise RuntimeError("rollback mismatch")
    p.unlink();sync_dir(root)
    return "rolled back"

def gate(root):
    root=check_root(root)
    p=root/"journal"
    pair=tuple((root/k).read_bytes() for k in NAMES)
    if not p.exists(): return pair==tuple(OLD[k] for k in NAMES)
    try:
        d=json.loads(p.read_bytes())
        return d=={"state":"committed","old":{k:digest(v) for k,v in OLD.items()},"new":{k:digest(v) for k,v in NEW.items()}} and pair==tuple(NEW[k] for k in NAMES)
    except (ValueError,TypeError):return False
