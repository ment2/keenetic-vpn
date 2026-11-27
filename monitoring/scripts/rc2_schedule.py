"""Bounded log launcher for existing RC2 schedule; no production writes."""
import os,sys,stat,subprocess,fcntl,time
from pathlib import Path
BASE=Path("/opt/var/lib/vpn-monitor")
STAGE=BASE/"rc2-stage"
def main():
 mode=sys.argv[1]
 if mode not in ("probe","publish"):raise ValueError("mode")
 s=BASE.lstat()
 if not stat.S_ISDIR(s.st_mode) or s.st_uid!=0 or s.st_mode&0o077:raise ValueError("directory")
 with os.fdopen(os.open(BASE/("rc2-"+mode+".launcher.lock"),os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600),"r+") as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return
  p=BASE/("rc2-"+mode+".log")
  if p.exists() and p.stat().st_size>131072:os.replace(p,p.with_suffix(".log.1"))
  with os.fdopen(os.open(p,os.O_WRONLY|os.O_APPEND|os.O_CREAT|os.O_NOFOLLOW,0o600),"a") as out:
   print(time.strftime("%Y-%m-%d %H:%M:%S"),mode,"START",file=out,flush=True)
   r=subprocess.run(["/opt/bin/python3","-B","-m","monitoring.rc2_cycle",mode],cwd=STAGE,stdout=out,stderr=out)
   print(time.strftime("%Y-%m-%d %H:%M:%S"),mode,"END",r.returncode,file=out,flush=True)
   raise SystemExit(r.returncode)
if __name__=="__main__":main()
