#!/opt/bin/python3
"""Prepared transaction helper; do not activate before staging/physical acceptance."""
import fcntl, hashlib, json, os, signal, stat, subprocess, sys, tempfile, time
from pathlib import Path
ROOT=Path('/proc'); TARGET=Path('/opt/etc/init.d/S98xray-wifi'); RULES=Path('/opt/bin/xray-wifi-rules.sh')
STAGE=Path('/tmp/s98-tproxy-rc2-20261127.py'); D=Path('/opt/etc/xray/s98-rc2-backup-20261127')
PID=Path('/opt/var/run/xray-wifi.pid'); ID=Path(str(PID)+'.identity'); REQUEST=Path(str(PID)+'.stop.json'); LIFE=Path(str(PID)+'.watch.lock'); CTRL=Path(str(PID)+'.control.lock')
UPDATE=Path('/opt/tmp/xray-update.lock'); PENDING=Path('/opt/etc/xray/config.pending.json'); PY='/opt/bin/python3'
OLD='6742e5e7f2a2bd41b85e9975371e7c46e66f0cfc6f5f843bf2c5dc1434c53601'; NEW='0c949c99f8605715bb981f1398ce04fa8ac433450fcca64772ad9f7e27fa7455'; RULEHASH='ead5de5555aaab1170a140ca3d41ea546330a99ba873b1961bee536bc12780ef'
class Block(RuntimeError): pass

def need(ok,msg):
    if not ok: raise Block(msg)
def read(p,expected=None):
    st=p.lstat(); need(stat.S_ISREG(st.st_mode) and st.st_uid==0,'UNSAFE_FILE '+p.name)
    b=p.read_bytes(); need(expected is None or hashlib.sha256(b).hexdigest()==expected,'HASH_DRIFT '+p.name); return b
def digest(p): return hashlib.sha256(read(p)).hexdigest()
def syncdir(p):
    fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)
def atomic(p,b,mode):
    fd,tmp=tempfile.mkstemp(prefix='.'+p.name+'.',dir=p.parent)
    try:
        with os.fdopen(fd,'wb') as f: f.write(b); os.fchmod(f.fileno(),mode); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,p); syncdir(p.parent)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
def exclusive(p,b):
    fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as f: f.write(b); f.flush(); os.fsync(f.fileno())
    syncdir(p.parent)
def boot(): return (ROOT/'sys/kernel/random/boot_id').read_text().strip()
def proc(pid):
    try:
        p=ROOT/str(pid); f=(p/'stat').read_text().rsplit(')',1)[1].split(); a=(p/'cmdline').read_bytes().rstrip(b'\0').split(b'\0')
        return (pid,f[19],f[0],int(f[1]),a)
    except (OSError,ValueError,IndexError): return None
def scan(): return [v for p in ROOT.iterdir() if p.name.isdigit() and (v:=proc(int(p.name))) and v[2]!='Z']
def role(p):
    a=p[4]; t=os.fsencode(TARGET)
    if len(a)==3 and a[0] in (b'/opt/bin/sh',b'/bin/sh') and a[1:]==[t,b'start']: return 'legacy'
    if len(a)==5 and a[:3]==[os.fsencode(PY),t,b'watch'] and all(x.isdigit() for x in a[3:]): return 'rc2'
    return None
def watchers(ps): return [p for p in ps if role(p)]
def identity(p): return (p[0],p[1],p[4])
def busy(ps):
    names={b'xray-wifi-rules.sh',b'xray-safe-hourly.sh',b'xray-update-v23.py',b'S97xray',b'rc.unslung'}
    return any(any(os.path.basename(a) in names for a in p[4][:4]) for p in ps)
def quiet(*a,t=12):
    r=subprocess.run(a,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=t)
    need(r.returncode==0,'COMMAND_FAILED '+os.path.basename(a[0])+' '+str(r.returncode)); return r.stdout

def gate():
    read(RULES,RULEHASH); need(not PENDING.exists(),'PENDING_CONFIG'); ps=scan(); need(not busy(ps),'COMPETING_WRITER')
    xs=[p for p in ps if p[4][0]==b'/opt/sbin/xray']; need(len(xs)==1,'XRAY_COUNT')
    return identity(xs[0])
def phase():
    j=json.loads(read(D/'phase.json')); need(j.get('boot')==boot() and j.get('old')==OLD and j.get('new')==NEW,'TRANSACTION_DRIFT'); return j['phase']
def state(phase): atomic(D/'phase.json',(json.dumps({'phase':phase,'boot':boot(),'old':OLD,'new':NEW})+'\n').encode(),0o600); print('PHASE',phase,flush=True)
def check():
    read(D/'candidate',NEW); quiet(PY,'-I','-B',str(D/'candidate'),'check',t=25)
def health(x):
    need(gate()==x,'XRAY_IDENTITY_CHANGED'); check()
    for url,code in [('https://www.gstatic.com/generate_204',b'204'),('https://api.openai.com/v1/models',b'401')]:
        r=quiet('/opt/bin/curl','-q','-sS','--noproxy','','--socks5-hostname','127.0.0.1:10808','--connect-timeout','3','--max-time','6','-o','/dev/null','-w','%{http_code}',url,t=8); need(r==code,'VPN_HEALTH_FAILED')
    print('HEALTH_OK HTTP204 HTTP401',flush=True)
def lock(p,create=False):
    fd=os.open(p,os.O_RDWR|os.O_NOFOLLOW|(os.O_CREAT if create else 0),0o600)
    try:
        st=os.fstat(fd); need(stat.S_ISREG(st.st_mode) and st.st_uid==0,'LOCK_INVALID'); need(os.path.samestat(st,p.lstat()),'LOCK_CHANGED'); fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB); return fd
    except BaseException: os.close(fd); raise

def prepare():
    need(digest(TARGET)==OLD and stat.S_IMODE(TARGET.stat().st_mode)==0o755,'ORIGINAL_DRIFT')
    read(RULES,RULEHASH); cand=read(STAGE,NEW); compile(cand,str(STAGE),'exec'); quiet(PY,'-I','-B',str(STAGE),'check',t=25)
    D.mkdir(mode=0o700); exclusive(D/'original',read(TARGET,OLD)); exclusive(D/'candidate',cand); state('PREPARED')
def legacy_stop(p,b):
    # Kernel 4.9 has no pidfd guarantee; compare exact identity immediately before TERM.
    ps=scan(); w=watchers(ps); need(boot()==b and len(w)==1 and identity(w[0])==identity(p) and role(w[0])=='legacy','LEGACY_DRIFT')
    need(not busy(ps) and all(os.path.basename(v[4][0])==b'sleep' for v in ps if v[3]==p[0]),'LEGACY_CHILD_ACTIVE')
    q=proc(p[0]); need(q and identity(q)==identity(p) and q[2]=='S','LEGACY_NOT_SLEEPING'); os.kill(p[0],signal.SIGTERM)
    for _ in range(40):
        q=proc(p[0]);
        if q is None or q[2]=='Z' or identity(q)!=identity(p): break
        time.sleep(.1)
    need(not watchers(scan()) and not busy(scan()),'LEGACY_STOP_UNCONFIRMED')
def clear_stale():
    need(not watchers(scan()) and not busy(scan()),'WATCHER_ACTIVE')
    for p in (PID,ID,REQUEST):
        if p.exists() or p.is_symlink(): read(p); p.unlink()

def install():
    need(phase()=='PREPARED','PHASE_DRIFT'); need(digest(TARGET)==OLD,'ORIGINAL_DRIFT'); read(D/'original',OLD); candidate=read(D/'candidate',NEW)
    check(); x=gate(); ps=scan(); w=watchers(ps); need(len(w)==1 and role(w[0])=='legacy','LEGACY_NOT_UNIQUE'); old=w[0]; b=boot(); health(x)
    state('INSTALL_INTENT'); need(digest(TARGET)==OLD,'ORIGINAL_DRIFT'); atomic(TARGET,candidate,0o755); state('FILE_RC2')
    legacy_stop(old,b); state('LEGACY_STOPPED'); clear_stale(); need(digest(TARGET)==NEW,'CANDIDATE_DRIFT'); need(gate()==x,'XRAY_IDENTITY_CHANGED')
def start():
    need(phase()=='LEGACY_STOPPED' and digest(TARGET)==NEW,'PHASE_DRIFT'); x=gate(); need(not watchers(scan()),'WATCHER_ACTIVE'); state('START_INTENT'); quiet(str(TARGET),'start',t=65); need(gate()==x,'XRAY_IDENTITY_CHANGED'); state('RC2_STARTED')
def verify():
    need(phase() in ('START_INTENT','RC2_STARTED','INITIAL_PASS') and digest(TARGET)==NEW,'PHASE_DRIFT'); x=gate(); ws=watchers(scan()); need(len(ws)==1 and role(ws[0])=='rc2','RC2_NOT_UNIQUE'); quiet(str(TARGET),'status',t=5); health(x); state('INITIAL_PASS')
def rollback_stop():
    phase(); read(D/'original',OLD); read(D/'candidate',NEW); gate(); h=digest(TARGET); need(h in (OLD,NEW),'TARGET_DRIFT'); ws=watchers(scan()); need(len(ws)<=1,'MULTIPLE_WATCHERS'); state('ROLLBACK_INTENT')
    if ws and role(ws[0])=='rc2':
        need(h==NEW,'RC2_FILE_MISMATCH'); quiet(str(TARGET),'stop',t=50); need(not watchers(scan()),'RC2_STOP_UNCONFIRMED')
    state('ROLLBACK_STOPPED')
def rollback_restore():
    need(phase()=='ROLLBACK_STOPPED','PHASE_DRIFT'); old=read(D/'original',OLD); read(D/'candidate',NEW); check(); gate(); h=digest(TARGET); need(h in (OLD,NEW),'TARGET_DRIFT'); ws=watchers(scan()); need(len(ws)<=1 and (not ws or role(ws[0])=='legacy'),'WATCHER_DRIFT')
    for p in (LIFE,CTRL):
        if p.exists(): fd=lock(p); os.close(fd)
    if h==NEW: atomic(TARGET,old,0o755)
    need(digest(TARGET)==OLD,'RESTORE_HASH_FAILED'); state('ORIGINAL_RESTORED')
    if not ws:
        clear_stale(); quiet(str(TARGET),'start',t=5)
    ws=watchers(scan()); need(len(ws)==1 and role(ws[0])=='legacy','LEGACY_START_UNCONFIRMED'); state('LEGACY_STARTED')
def rollback_verify():
    need(phase() in ('LEGACY_STARTED','ORIGINAL_RESTORED','ROLLBACK_PASS') and digest(TARGET)==OLD,'PHASE_DRIFT'); x=gate(); ws=watchers(scan()); need(len(ws)==1 and role(ws[0])=='legacy','LEGACY_NOT_UNIQUE'); health(x); state('ROLLBACK_PASS')
def main():
    need(os.geteuid()==0,'ROOT_REQUIRED'); actions={'prepare':prepare,'install':install,'start':start,'verify':verify,'rollback-stop':rollback_stop,'rollback-restore':rollback_restore,'rollback-verify':rollback_verify}; need(len(sys.argv)==2 and sys.argv[1] in actions,'INVALID_ACTION'); a=sys.argv[1]
    # Never remove the updater lock. Bound control operations to the existing lock inode.
    need(UPDATE.lstat().st_ino==1280,'UPDATE_LOCK_DRIFT'); fd=lock(UPDATE)
    try:
        if a=='prepare': prepare(); return
        st=D.lstat(); need(stat.S_ISDIR(st.st_mode) and st.st_uid==0 and stat.S_IMODE(st.st_mode)==0o700,'BACKUP_DIRECTORY_INVALID'); read(D/'phase.json')
        actions[a]()
    finally: os.close(fd)
if __name__=='__main__':
    try: main()
    except (Block,OSError,ValueError,subprocess.SubprocessError) as e:
        print('S98_SWITCH_BLOCKED',type(e).__name__,str(e),file=sys.stderr); sys.exit(1)
