"""Execute a version-pinned copy of the existing *real shell source* against
disposable fake iptables to reproduce TPROXY append error being suppressed.

Never reads or writes any router, does not launch real iptables/ip.
"""
import json,os,subprocess,tempfile,hashlib
from pathlib import Path
from .rc44_tproxy_repair_gate import SOURCE,SOURCE_SHA256,EXCEPTIONS

FAKE_IPT=r'''#!/usr/bin/env python3
import sys,os,json
from pathlib import Path
args=sys.argv[1:];path=Path(os.environ["RC44_FAKE_STATE"])
d=json.loads(path.read_text())
if args[0:3]==["-t","mangle","-N"]:pass
elif args[0:3]==["-t","mangle","-F"]:d["chain"]=[]
elif args[0:3]==["-t","mangle","-A"]:
 if "-j" in args and args[args.index("-j")+1]=="TPROXY":
  d["tproxy_attempts"]+=1
  path.write_text(json.dumps(d))
  print("xt_TPROXY hypothetical kernel rejection",file=sys.stderr)
  sys.exit(4)
 if "-d" in args and "-j" in args and args[args.index("-j")+1]=="RETURN":
  d["chain"].append(args[args.index("-d")+1])
elif args[0:3]==["-t","mangle","-C"]:
 if "PREROUTING" not in args:sys.exit(3)
else:
 print("UNEXPECTED_FAKE_IPTABLES",args,file=sys.stderr);sys.exit(9)
path.write_text(json.dumps(d))
'''
FAKE_IP=r'''#!/bin/sh
case "$1 $2" in
 "rule show") printf '%s\n' '20000: from all fwmark 0x40000000/0x40000000 lookup 100';;
 "route replace") exit 0;;
 *) echo UNEXPECTED_FAKE_IP >&2; exit 9;;
esac
'''
def reproduce():
 raw=SOURCE.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA256:
  raise RuntimeError("UNPINNED_WIFI_RULE_SOURCE")
 with tempfile.TemporaryDirectory(prefix="rc44-source-failure-") as td:
  root=Path(td);binary=root/"iptables";fakeip=root/"ip";state=root/"state.json"
  script=root/"xray-wifi-source-copy.sh"
  binary.write_text(FAKE_IPT)
  fakeip.write_text(FAKE_IP)
  binary.chmod(0o700);fakeip.chmod(0o700)
  text=raw.decode().replace("IPT=/opt/sbin/iptables","IPT="+str(binary),1)
  script.write_text(text)
  state.write_text(json.dumps({"chain":[],"tproxy_attempts":0}))
  env=dict(os.environ,RC44_FAKE_STATE=str(state),PATH=str(root)+":"+os.environ.get("PATH",""))
  p=subprocess.run(["/bin/sh",str(script)],env=env,capture_output=True,text=True,timeout=15)
  observed=json.loads(state.read_text())
  if p.returncode!=0 or observed["chain"]!=list(EXCEPTIONS) or observed["tproxy_attempts"]!=2:
   raise RuntimeError("RC44_FAKE_SOURCE_EXPERIMENT_DRIFT")
  return {"shell_exit_code":p.returncode,"return_destinations":len(observed["chain"]),
          "tproxy_add_failures":observed["tproxy_attempts"],
          "witness":"PINNED_VERSIONED_SHELL_RETURNS_0_AFTER_BOTH_TPROXY_APPEND_FAILURES",
          "proof_scope":"MOCK_KERNEL_REJECTION_NOT_OBSERVED_REAL_ROUTER_ERRNO",
          "production_authorized":False}
if __name__=="__main__":
 print(json.dumps(reproduce(),sort_keys=True))
