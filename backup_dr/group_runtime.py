"""One receiver port, separate authenticated groups, independent state and quotas.
Candidate only. No installation, cron or key generation performed here.
"""
import fcntl, pathlib, os
from groups import validate, preflight, group_key, config_id
from runtime import tick
from transport import receiver
from monitor import status
from retention import prune
from resource_guard import CIPHER_MAX

TOTAL_BUDGET=2*1024**3
RESERVE=5*1024**3

def private_dir(path):
    path=pathlib.Path(path)
    path.mkdir(mode=0o700,parents=False,exist_ok=True)
    if path.is_symlink() or not path.is_dir() or path.stat().st_mode & 0o077: raise ValueError('insecure directory')
    return path

def make_receiver(root,master,config,quotas,allowed_ip,bind,*,total_budget=TOTAL_BUDGET,reserve=RESERVE,status_inbox=None):
    config=validate(config)
    if set(quotas)!=set(config) or any(type(q) is not int or q<=0 for q in quotas.values()) or sum(quotas.values())>total_budget or not 0<total_budget<=TOTAL_BUDGET: raise ValueError('invalid group quotas')
    root=private_dir(root); routes={}
    for group,entries in config.items():
        folder=private_dir(root/group)
        routes['/v1/backup/'+group]=(folder,group_key(master,group),quotas[group],entries)
    return receiver(root,master,allowed_ip,bind,routes=routes,reserve=reserve,global_budget=total_budget,body_limit=CIPHER_MAX,status_inbox=status_inbox)

def run_tick(state_root,source_root,config,master,origin,*,now=None):
    config=validate(config); root=private_dir(state_root); results={}
    with (root/'groups.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for group,entries in sorted(config.items()):
            try:
                folder=private_dir(root/group); state=private_dir(folder/config_id(entries))
                results[group]=tick(state,source_root,entries,group_key(master,group),origin.rstrip('/')+'/v1/backup/'+group,now=now,source_ready=lambda:preflight(source_root,{group:entries})[group]['ready'])
            except (OSError,ValueError,MemoryError,TimeoutError):
                results[group]='retry_required'
    return results

def group_status(root,config,*,now=None,reserve=RESERVE,total_budget=TOTAL_BUDGET):
    config=validate(config); rows={g:status(pathlib.Path(root)/g,now=now,reserve=reserve) for g in config}
    first=next(iter(rows.values())); latest=[x['latest_archive_mtime'] for x in rows.values() if x['latest_archive_mtime'] is not None]
    from global_quota import usage,locked
    with locked(root): used=usage(root)
    return {'version':1,'receiver_heartbeat':first['receiver_heartbeat'],'global_used_bytes':used,'global_budget_bytes':total_budget,'status':'low_space' if any(r['status']=='low_space' for r in rows.values()) else 'quota_full' if used>=total_budget else 'ready' if all(r['archive_count'] for r in rows.values()) else 'awaiting_first_backup','archive_count':sum(r['archive_count'] for r in rows.values()),'archive_bytes':sum(r['archive_bytes'] for r in rows.values()),'latest_archive_mtime':max(latest) if latest else None,'free_bytes':first['free_bytes'],'groups':rows}

def prune_groups(root,config,master,*,now=None):
    # Invoke only inside the receiver's single-threaded maintenance loop.
    from global_quota import locked
    with locked(root):
        return {g:prune(pathlib.Path(root)/g,group_key(master,g),now=now) for g in validate(config)}
