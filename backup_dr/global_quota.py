"""Global accounting for the dedicated archive tree, including retired groups.
Only cooperating receiver/maintenance processes may modify this private tree.
"""
import contextlib, fcntl, os, pathlib, stat, shutil
from quota import QuotaExceeded

@contextlib.contextmanager
def locked(root):
    root=pathlib.Path(root)
    if root.is_symlink() or not root.is_dir() or root.stat().st_mode & 0o077:
        raise ValueError('insecure global storage root')
    fd=os.open(root/'.quota.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode): raise ValueError('invalid lock')
        fcntl.flock(fd,fcntl.LOCK_EX)
        yield
    finally: os.close(fd)

def usage(root):
    root=pathlib.Path(root)
    st=root.lstat()
    if not stat.S_ISDIR(st.st_mode): raise ValueError('invalid storage root')
    total=0; stack=[root]
    while stack:
        with os.scandir(stack.pop()) as items:
            for item in items:
                s=item.stat(follow_symlinks=False)
                if s.st_dev!=st.st_dev: raise ValueError('foreign storage mount')
                if stat.S_ISDIR(s.st_mode): stack.append(pathlib.Path(item.path))
                elif stat.S_ISREG(s.st_mode): total+=s.st_size
                else: raise ValueError('unexpected storage entry')
    return total

def check(root, directory, size, budget, reserve):
    root=pathlib.Path(root); directory=pathlib.Path(directory)
    if directory.parent!=root or directory.is_symlink() or not directory.is_dir(): raise ValueError('invalid group directory')
    if any(type(n) is not int for n in (size,budget,reserve)) or size<0 or budget<=0 or reserve<0: raise ValueError('invalid global quota')
    used=usage(root)
    if used+size>budget or shutil.disk_usage(root).free-size<reserve: raise QuotaExceeded('global backup quota')
    return used
