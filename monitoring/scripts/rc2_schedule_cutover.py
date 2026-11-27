"""RC2 monitor-only schedule cutover. No VPN service or firewall operations."""
import os,stat,hashlib,time,subprocess,pathlib,signal,fcntl,tempfile,json
P=pathlib.Path
BASE=P("/opt/var/lib/vpn-monitor")
INIT=P("/opt/etc/init.d/S99zz-vpn-monitoring")
STAGE=BASE/"rc2-stage"
BACK=BASE/"rc2-schedule-backup-20261127"
OLD_CRON=b'*/15 * * * * cd /opt/tmp/vpn-monitoring-lab && PYTHONDONTWRITEBYTECODE=1 /opt/bin/python3 -B -m monitoring.openai_health_collector_loop --max-cycles 1 --publish >> /opt/var/log/vpn-openai-health.log 2>&1'
OLD_START=b'   start_one health monitoring.vpn_health_collector_loop "$RUN/vpn-vless-health.pid" "$BASE/vpn-health.log" 900\n'
OLD_STOP=b'   stop_one health monitoring.vpn_health_collector_loop "$RUN/vpn-vless-health.pid"\n'
NEW_LINES=(b'3,18,33,48 * * * * /opt/bin/python3 -B /opt/var/lib/vpn-monitor/rc2-stage/rc2_schedule.py probe\n'
           b'* * * * * /opt/bin/python3 -B /opt/var/lib/vpn-monitor/rc2-stage/rc2_schedule.py publish\n')
def sha(b):return hashlib.sha256(b).hexdigest()
def require(ok,reason):
 if not ok:raise RuntimeError(reason)
def cron():return subprocess.check_output(["crontab","-l"])
def atomic(p,b,mode):
 fd,n=tempfile.mkstemp(prefix=".rc2-",dir=p.parent)
 try:
  with os.fdopen(fd,"wb") as f:os.fchmod(f.fileno(),mode);f.write(b);f.flush();os.fsync(f.fileno())
  os.replace(n,p)
 finally:
  if os.path.exists(n):os.unlink(n)
def install_cron(b):
 p=BACK/"cron.install";atomic(p,b,0o600)
 subprocess.run(["crontab",str(p)],check=True)
 require(cron()==b,"cron readback")
def processes():
 out={}
 for p in P("/proc").glob("[0-9]*"):
  try:
   a=(p/"cmdline").read_bytes().split(bytes([0]));s=(p/"stat").read_text().rsplit(")",1)[1].split()
   out[int(p.name)]=(int(s[1]),s[19],a)
  except (OSError,ValueError,IndexError):pass
 return out
def matching(ps,mod):return [k for k,v in ps.items() if mod.encode() in v[2]]
def witness():
 ps=processes()
 main=[(k,v[1]) for k,v in ps.items() if v[2] and v[2][0].endswith(b"/xray") and b"/opt/etc/xray/config.json" in v[2]]
 return main,sha(P("/opt/etc/xray/config.json").read_bytes()),sha(P("/opt/bin/xray-update-v23.py").read_bytes()),sha(P("/opt/bin/xray-safe-hourly.sh").read_bytes())
def rollback(old_i,old_c,mode,new_i,new_c,stopped):
 # Restore only exact known generations; do not overwrite a foreign edit.
 require(INIT.read_bytes() in (old_i,new_i) and cron() in (old_c,new_c),"rollback CAS")
 atomic(INIT,old_i,mode);install_cron(old_c)
 if stopped:
  require(not matching(processes(),"monitoring.vpn_health_collector_loop"),"old collector unexpectedly present")
  subprocess.run(["/opt/sbin/start-stop-daemon","-S","-b","-d","/opt/tmp/vpn-monitoring-lab","-p","/opt/var/run/vpn-vless-health.pid","-m","-x","/opt/bin/python3","-O","/opt/tmp/vpn-monitoring-lab/vpn-health.log","--","-u","-B","-m","monitoring.vpn_health_collector_loop","--interval","900","--publish"],check=True)
def main():
 require(4<=time.localtime().tm_min%15<=10,"quiet window")
 old_i=INIT.read_bytes();old_c=cron();mode=stat.S_IMODE(INIT.stat().st_mode)
 require(sha(old_i)=="abea4530831916ddc92eac4742a5f9a528a3efc4188a9e13f3305cc4a3d855af","init changed")
 require(sha(old_c)=="fb3f3871bcf79a83739f14dbaa8817b262bedb1c1cd0907b4594f709cd6da6c3","cron changed")
 require(old_c.count(OLD_CRON+b"\n")==1 and old_i.count(OLD_START)==1 and old_i.count(OLD_STOP)==1,"old schedule unexpected")
 new_i=old_i.replace(OLD_START,b"   # RC2 health is scheduled by cron.\n").replace(OLD_STOP,b"   # RC2 health is scheduled by cron.\n")
 new_c=old_c.replace(OLD_CRON+b"\n",NEW_LINES)
 require(new_c.endswith(b"\n"),"cron newline")
 require((STAGE/"rc2_schedule.py").is_file(),"schedule launcher missing")
 before=witness();require(len(before[0])==1,"main Xray ambiguous")
 ps=processes();h=matching(ps,"monitoring.vpn_health_collector_loop");tr=matching(ps,"monitoring.traffic_collector_loop")
 require(len(h)==len(tr)==1 and not matching(ps,"monitoring.openai_health_collector_loop") and not matching(ps,"monitoring.rc2_cycle"),"collector inventory")
 pid=h[0];ident=ps[pid]
 require(not any(v[0]==pid for v in ps.values()),"health collector busy")
 require(60<=time.time()-P("/opt/tmp/vpn-monitoring-lab/vpn-health.log").stat().st_mtime<=700,"health quiet window")
 require(not any(v[2] and v[2][0].endswith(b"/xray") and k!=before[0][0][0] for k,v in ps.items()),"temporary Xray present")
 BACK.mkdir(mode=0o700,exist_ok=False)
 atomic(BACK/"init.before",old_i,0o600);atomic(BACK/"cron.before",old_c,0o600)
 atomic(BACK/"init.after",new_i,0o600);atomic(BACK/"cron.after",new_c,0o600)
 atomic(BACK/"manifest.json",json.dumps({"init_before":sha(old_i),"cron_before":sha(old_c),"init_after":sha(new_i),"cron_after":sha(new_c),"mode":mode}).encode(),0o600)
 subprocess.run(["/bin/sh","-n",str(BACK/"init.after")],check=True)
 stopped=False
 try:
  require(INIT.read_bytes()==old_i and cron()==old_c,"schedule CAS")
  ps=processes();require(ps.get(pid)==ident and not any(v[0]==pid for v in ps.values()),"collector identity or children changed")
  # TERM sets old collector's graceful stop flag; no forced kill.
  os.kill(pid,signal.SIGTERM)
  for _ in range(25):
   if pid not in processes():stopped=True;break
   time.sleep(.2)
  require(stopped,"old collector did not stop")
  require(not matching(processes(),"monitoring.vpn_health_collector_loop"),"old collector still present")
  atomic(INIT,new_i,mode);install_cron(new_c)
  require(INIT.read_bytes()==new_i,"init readback")
  require(witness()==before,"VPN witness changed")
  require(processes().get(tr[0])==ps.get(tr[0]),"traffic collector changed")
  print("RC2_CUTOVER_OK",sha(new_i),sha(new_c),"traffic_unchanged",True,flush=True)
 except BaseException:
  rollback(old_i,old_c,mode,new_i,new_c,stopped)
  print("RC2_CUTOVER_ROLLBACK",flush=True);raise
if __name__=="__main__":
 try:main()
 except Exception as exc:print("RC2_CUTOVER_BLOCKED",type(exc).__name__,str(exc) if isinstance(exc,RuntimeError) else "",flush=True);raise SystemExit(1)
