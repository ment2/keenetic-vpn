"""Foreground receiver and single scheduler tick; no install or auto-start."""
import argparse, contextlib, fcntl, json, os, pathlib, signal, stat, sys, time
from groups import validate, preflight
from group_runtime import make_receiver, run_tick, group_status, private_dir, TOTAL_BUDGET, RESERVE, prune_groups
from monitor import publish
from retention import prune
from groups import group_key
from global_quota import locked
from sender_monitor import Inbox,send_report

RECEIVER_IP = '192.168.0.169'
SENDER_IP = '192.168.0.135'
PORT = 8765

def load_plan(path):
    p = json.loads(pathlib.Path(path).read_text())
    if set(p) != {'version','groups','quotas'} or p['version'] != 1:
        raise ValueError('invalid plan schema')
    config = validate(p['groups']); quotas = p['quotas']
    if not isinstance(quotas,dict) or set(quotas)!=set(config) or any(type(q) is not int or q<=0 for q in quotas.values()) or sum(quotas.values())>TOTAL_BUDGET:
        raise ValueError('invalid quota plan')
    return config, quotas

def local_master(path):
    # Operational master supplied locally by owner; never generated or printed here.
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        s=os.fstat(fd)
        if not stat.S_ISREG(s.st_mode) or s.st_mode & 0o077 or s.st_uid!=os.geteuid() or s.st_size!=32:
            raise ValueError('insecure key file')
        data=os.read(fd,33)
        if len(data)!=32: raise ValueError('invalid key length')
        return data
    finally: os.close(fd)

@contextlib.contextmanager
def exclusive(path):
    fd=os.open(path,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        s=os.fstat(fd)
        if not stat.S_ISREG(s.st_mode) or s.st_mode&0o077 or s.st_uid!=os.geteuid(): raise ValueError('invalid service lock')
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        yield
    finally: os.close(fd)

def maintenance(root, config, master, now=None):
    return {g:len(v) for g,v in prune_groups(root,config,master,now=now).items()}

def run_receiver(server, root, config, master, status_path, *, stop=lambda:False, clock=time.monotonic, interval=30, retention_interval=3600, reserve=RESERVE, status_inbox=None):
    server.timeout=min(interval,5)
    next_status=next_retention=clock()
    error=False
    try:
        while not stop():
            now=clock()
            if now>=next_retention:
                try: maintenance(root,config,master); error=False
                except (OSError,ValueError): error=True
                next_retention=clock()+retention_interval
            if now>=next_status:
                record=group_status(root,config,reserve=reserve)
                record['retention_error']=error
                if status_inbox is not None: record['sender']=status_inbox.summary()
                publish(status_path,record)
                next_status=clock()+interval
            if not stop(): server.handle_request()
    finally: server.server_close()

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('mode',choices=('receiver','tick','preflight'))
    ap.add_argument('--plan',required=True); ap.add_argument('--key'); ap.add_argument('--root',required=True)
    ap.add_argument('--sender-state'); ap.add_argument('--source-root',default='/opt'); ap.add_argument('--status'); ap.add_argument('--enable',action='store_true')
    a=ap.parse_args(argv); os.umask(0o077)
    config,quotas=load_plan(a.plan)
    if a.mode=='preflight':
        rows=preflight(a.source_root,config); print(json.dumps(rows,sort_keys=True)); return 0 if all(r['ready'] for r in rows.values()) else 1
    if not a.enable or not a.key or not a.status: ap.error('explicit --enable, --key and --status required')
    root=private_dir(a.root); master=local_master(a.key)
    status_path=pathlib.Path(a.status)
    if status_path.resolve()!=status_path.absolute() or not status_path.parent.is_dir(): raise ValueError('invalid status path')
    with exclusive(root/'service.lock'):
        if a.mode=='tick':
            results=run_tick(root,a.source_root,config,master,f'http://{RECEIVER_IP}:{PORT}')
            record={'version':1,'scheduler_heartbeat':int(time.time()),'groups':results,'status':'retry_required' if any(r not in ('idle','accepted') for r in results.values()) else 'ok'}
            try: send_report(f'http://{RECEIVER_IP}:{PORT}',master,results)
            except (OSError,ValueError): record['telemetry_error']=True
            else: record['telemetry_error']=False
            publish(status_path,record); return int(record['status']!='ok' or record['telemetry_error'])
        if not a.sender_state: ap.error('receiver requires --sender-state in separate private directory')
        sp=pathlib.Path(a.sender_state).absolute()
        if sp.is_relative_to(root.resolve()) or sp==status_path.absolute(): raise ValueError('sender state must be separate from archive tree and public status')
        inbox=Inbox(sp,master,config)
        server=make_receiver(root,master,config,quotas,SENDER_IP,(RECEIVER_IP,PORT),status_inbox=inbox); stopping=False
        def halt(*_):
            nonlocal stopping
            stopping=True
        signal.signal(signal.SIGTERM,halt); signal.signal(signal.SIGINT,halt)
        run_receiver(server,root,config,master,status_path,stop=lambda:stopping,status_inbox=inbox)
        return 0

if __name__=='__main__':
    try: sys.exit(main())
    except (ValueError,OSError,MemoryError,KeyError,TypeError):
        print('BACKUP_DR_SERVICE_ERROR',file=sys.stderr); sys.exit(1)
