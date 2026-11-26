"""Reject new blobs before exceeding a dedicated receiver's storage budget."""
import os, pathlib, shutil
class QuotaExceeded(ValueError): pass

def check(root, size, budget, reserve):
    if budget<=0 or reserve<0 or size<0: raise ValueError('invalid quota')
    root=pathlib.Path(root)
    used=sum(p.lstat().st_size for p in root.iterdir() if p.is_file() and not p.is_symlink())
    if used+size>budget or shutil.disk_usage(root).free-size<reserve: raise QuotaExceeded('backup quota')
    return used
