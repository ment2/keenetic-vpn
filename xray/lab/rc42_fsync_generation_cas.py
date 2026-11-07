"""EPHEMERAL runner fsync+directory-fsync CAS; never physical rescue evidence."""
import os,json,fcntl,tempfile,hashlib,argparse
from pathlib import Path
class CASBlocked(ValueError):pass
def tag(rec):return hashlib.sha256(json.dumps(rec,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def write(root,body,inject=False):
 obj=dict(body,checksum=tag(body))
 fd,tmp=tempfile.mkstemp(prefix=".staged-",dir=root)
 try:
  with os.fdopen(fd,"wb") as f:
   f.write((json.dumps(obj,sort_keys=True)+"\n").encode());f.flush();os.fsync(f.fileno())
  if inject:raise CASBlocked("INJECTED_PRE_REPLACE_FAILURE")
  os.replace(tmp,root/"receipt.json")
  d=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
  try:os.fsync(d)
  finally:os.close(d)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
def read(root):
 p=Path(root)/"receipt.json"
 if p.is_symlink() or not p.is_file():raise CASBlocked("MISSING_OR_SYMLINKED_RECEIPT")
 obj=json.loads(p.read_text());t=obj.pop("checksum",None)
 if t!=tag(obj):raise CASBlocked("BAD_JOURNAL_CHECKSUM")
 if obj["generation"]<1 or len(obj["boot"])!=36 or len(obj["rules_sha"])!=64:raise CASBlocked("BAD_JOURNAL_IDENTITY")
 return obj
def begin(root,boot,rules_sha,pid,ticks):
 root=Path(root);root.mkdir(mode=0o700,parents=True,exist_ok=False)
 obj=dict(generation=1,phase="ORIGINAL",boot=boot,rules_sha=rules_sha,pid=int(pid),ticks=str(ticks))
 write(root,obj);return read(root)
def advance(root,expected,old_phase,new_phase,boot,old_sha,new_sha,pid,ticks,inject=False):
 root=Path(root)
 fd=os.open(root/"lease.lock",os.O_WRONLY|os.O_CREAT|os.O_NOFOLLOW,0o600)
 try:
  fcntl.flock(fd,fcntl.LOCK_EX)
  obj=read(root)
  if (obj["generation"]!=expected or obj["phase"]!=old_phase or obj["boot"]!=boot
    or obj["rules_sha"]!=old_sha or obj["pid"]!=pid or obj["ticks"]!=str(ticks)):
   raise CASBlocked("STALE_BOOT_PID_TICKS_RULES_OR_GENERATION")
  nxt=dict(obj,generation=expected+1,phase=new_phase,rules_sha=new_sha)
  write(root,nxt,inject);return read(root)
 finally:
  fcntl.flock(fd,fcntl.LOCK_UN);os.close(fd)
def main():
 p=argparse.ArgumentParser()
 p.add_argument("op",choices=("begin","advance","inspect"))
 p.add_argument("--root",type=Path,required=True)
 p.add_argument("--boot",default="");p.add_argument("--sha",default="")
 p.add_argument("--new-sha",default="");p.add_argument("--pid",type=int,default=0)
 p.add_argument("--ticks",default="");p.add_argument("--expected",type=int,default=0)
 p.add_argument("--old-phase",default="");p.add_argument("--new-phase",default="")
 x=p.parse_args()
 if x.op=="begin":o=begin(x.root,x.boot,x.sha,x.pid,x.ticks)
 elif x.op=="advance":o=advance(x.root,x.expected,x.old_phase,x.new_phase,x.boot,x.sha,x.new_sha,x.pid,x.ticks)
 else:o=read(x.root)
 print("RC42_RUNNER_FSYNC_DIR_CAS",o["generation"],o["phase"],o["rules_sha"])
 print("RC42_HARD_NO_GO_EPHEMERAL_FSYNC_NOT_POWER_LOSS_OR_USB_FREE_RESCUE")
if __name__=="__main__":main()
