"""Monitor-only cutover, Keenetic RC2. Never modifies VPN service or updater."""
import os,sys,time,stat,signal,hashlib,subprocess,tempfile,pathlib,fcntl,json
P=pathlib.Path
BASE=P("/opt/var/lib/vpn-monitor")
STAGE=BASE/"rc2-stage"
INIT=P("/opt/etc/init.d/S99zz-vpn-monitoring")
PIDFILE=P("/opt/var/run/vpn-vless-health.pid")
PY="/opt/bin/python3"
OLD_INIT="abea4530831916ddc92eac4742a5f9a528a3efc4188a9e13f3305cc4a3d855af"
OLD_CRON="fb3f3871bcf79a83739f14dbaa8817b262bedb1c1cd0907b4594f709cd6da6c3"
OLD_LINE="*/15 * * * * cd /opt/tmp/vpn-monitoring-lab && PYTHONDONTWRITEBYTECODE=1 /opt/bin/python3 -B -m monitoring.openai_health_collector_loop --max-cycles 1 --publish >> /opt/var/log/vpn-openai-health.log 2>&1"
BLOBS={"rc2_cycle.py":"caf2157464bdff30805f7d35aaf73619871becaa","rc2_probe.py":"3da51952133ea1e4978d845e415736a7fb938ef6","rc2_snapshot.py":"db6c883b55b6ae698783062aa2b9c780c59a5f1c","rc2_history.py":"9d0a5d61f138603255bba8b3e641a7c2a7a84f90","dynamic_monitor_cycle.py":"35b178ca128e603e24386beea89f221f464f927a","full_subscription_snapshot.py":"8633dcd6c7cc5abe28966419296fd5de12601244"}
def require(ok,why):
    if not ok:raise RuntimeError(why)
def digest(b):return hashlib.sha256(b).hexdigest()
def cron():return subprocess.check_output(["crontab","-l"])
def atomic(p,b,mode):
    fd,n=tempfile.mkstemp(dir=p.parent,prefix=".rc2-")
    try:
        with os.fdopen(fd,"wb") as f:
            os.fchmod(f.fileno(),mode);f.write(b);f.flush();os.fsync(f.fileno())
        os.replace(n,p)
    finally:
        if os.path.exists(n):os.unlink(n)
def install_cron(b,d):
    p=d/"cron.install";atomic(p,b,0o600)
    subprocess.run(["crontab",str(p)],check=True,timeout=10)
    require(cron()==b,"cron readback")
def processes():
    rows={}
    for p in P("/proc").glob("[0-9]*"):
        try:
            s=(p/"stat").read_text().rsplit(")",1)[1].split()
            a=(p/"cmdline").read_bytes().split(bytes([0]))
            rows[int(p.name)]=(int(s[1]),s[19],a)
        except (OSError,ValueError,IndexError):pass
    return rows
def module(rows,name):
    return [(pid,v[1]) for pid,v in rows.items() if name.encode() in v[2]]
def descendants(rows,pid):
    out={pid}
    while True:
        new=out|{k for k,v in rows.items() if v[0] in out}
        if new==out:return out-{pid}
        out=new
def start_old():
    subprocess.run(["/opt/sbin/start-stop-daemon","-S","-b","-d","/opt/tmp/vpn-monitoring-lab","-p",str(PIDFILE),"-m","-x",PY,"-O","/opt/tmp/vpn-monitoring-lab/vpn-health.log","--","-u","-B","-m","monitoring.vpn_health_collector_loop","--interval","900","--publish"],check=True,timeout=10)
def new_cron(c):
    s=c.decode();require(s.splitlines().count(OLD_LINE)==1,"old cron line mismatch")
    lines=[x for x in s.splitlines(keepends=True) if x.rstrip("\n")!=OLD_LINE]
    require(not any("monitoring.rc2_cycle" in x for x in lines),"already scheduled")
    for mode,spec in (("probe","3,18,33,48"),("publish","*")):
        lines.append(spec+" * * * * umask 077; cd "+str(STAGE)+" && "+PY+" -B -m monitoring.rc2_cycle "+mode+" > "+str(BASE/("rc2-"+mode+".log"))+" 2>&1\n")
    return "".join(lines).encode()
def main():
    os.umask(0o077)
    c=cron();i=INIT.read_bytes();mode=stat.S_IMODE(INIT.stat().st_mode)
    require(digest(c)==OLD_CRON and digest(i)==OLD_INIT,"baseline CAS")
    for n,want in BLOBS.items():
        b=(STAGE/"monitoring"/n).read_bytes()
        require(hashlib.sha1(("blob %d"%len(b)).encode()+bytes([0])+b).hexdigest()==want,"staging mismatch")
        compile(b,n,"exec")
    pins=json.loads(P("/opt/etc/vpn-monitor/dynamic-source-pins.json").read_bytes())
    require(len(pins)==4 and all(digest((P("/opt/bin")/k).read_bytes())==v for k,v in pins.items()),"pins mismatch")
    nc=new_cron(c)
    ni=b"".join(l for l in i.splitlines(keepends=True) if not l.lstrip().startswith((b"start_one health ",b"stop_one health ")))
    require(ni!=i and len(i.splitlines())-len(ni.splitlines())==2,"init diff")
    require(b"start_one traffic " in ni and b"stop_one traffic " in ni,"traffic changed")
    subprocess.run(["/bin/sh","-n"],input=ni,check=True,timeout=5)
    # Avoid old OpenAI cron boundary and the RC2 probe start minute.
    require(4<=time.localtime().tm_min%15<=11,"outside monitor switch window")
    rows=processes();old=module(rows,"monitoring.vpn_health_collector_loop");traffic=module(rows,"monitoring.traffic_collector_loop")
    require(len(old)==1 and len(traffic)==1 and not module(rows,"monitoring.openai_health_collector_loop"),"old collector state")
    pid,ticks=old[0];require(PIDFILE.read_text().strip()==str(pid),"old pidfile mismatch")
    # Old collector handles TERM gracefully. Wait for a child-free, recently
    # completed round, rather than signalling an active probe.
    end=time.monotonic()+70
    while True:
        rows=processes()
        require(module(rows,"monitoring.vpn_health_collector_loop")==old and module(rows,"monitoring.traffic_collector_loop")==traffic,"process changed")
        age=time.time()-P("/opt/tmp/vpn-monitoring-lab/vpn-health.log").stat().st_mtime
        if 2<=age<=650 and not descendants(rows,pid) and not module(rows,"monitoring.openai_health_collector_loop"):break
        require(time.monotonic()<end,"old collector still busy")
        time.sleep(2)
    require(4<=time.localtime().tm_min%15<=11,"window closed")
    # Ensure no updater in progress at switch instant; don't create or
    # modify its lock. RC2 continues to use its existing idle checks.
    with open("/opt/tmp/xray-update.lock","rb") as f:fcntl.flock(f,fcntl.LOCK_SH|fcntl.LOCK_NB)
    require(cron()==c and INIT.read_bytes()==i,"fresh CAS")
    d=BASE/("rc2-cutover-backup-"+str(int(time.time())));d.mkdir(mode=0o700)
    for n,b in (("init.before",i),("cron.before",c),("init.after",ni),("cron.after",nc)):
        atomic(d/n,b,0o600);require((d/n).read_bytes()==b,"backup readback")
    atomic(d/"SHA256SUMS",("".join(digest((d/n).read_bytes())+"  "+n+"\n" for n in ("init.before","cron.before","init.after","cron.after"))).encode(),0o600)
    print("BACKUP",d.name,flush=True)
    init_changed=False;cron_changed=False;stopped=False
    try:
        atomic(INIT,ni,mode);init_changed=True
        require(INIT.read_bytes()==ni,"init readback")
        rows=processes();require(module(rows,"monitoring.vpn_health_collector_loop")==old and not descendants(rows,pid),"old process no longer idle")
        os.kill(pid,signal.SIGTERM)
        end=time.monotonic()+12
        while module(processes(),"monitoring.vpn_health_collector_loop"):
            require(time.monotonic()<end,"old collector did not stop");time.sleep(.25)
        stopped=True
        require(not module(processes(),"monitoring.openai_health_collector_loop"),"old OpenAI running")
        require(cron()==c,"cron changed")
        cron_changed=True;install_cron(nc,d)
        require(module(processes(),"monitoring.traffic_collector_loop")==traffic,"traffic collector changed")
        print("CUTOVER_OK","old_health_stopped",True,"traffic_unchanged",True,"cron_sha",digest(nc),"init_sha",digest(ni),flush=True)
    except BaseException:
        if cron_changed:
            current=cron();require(current in (c,nc),"rollback cron conflict")
            if current!=c:install_cron(c,d)
        if init_changed:
            require(INIT.read_bytes() in (i,ni),"rollback init conflict")
            if INIT.read_bytes()!=i:atomic(INIT,i,mode)
        if stopped and not module(processes(),"monitoring.vpn_health_collector_loop"):start_old()
        print("CUTOVER_ROLLED_BACK",flush=True);raise
if __name__=="__main__":
    try:main()
    except Exception as e:
        print("CUTOVER_BLOCKED",str(e) if type(e) is RuntimeError else type(e).__name__,flush=True);sys.exit(1)
