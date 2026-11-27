"""Read-only production witnesses around an isolated candidate trial.

This file is an acceptance harness, not a production installer. It must only
run under an explicitly authorized quiet-window MCP task. No detached work,
no actual config/pending writes, no routes/firewall changes.
"""
import collections
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import time

ROOT=Path("/opt/var/lib/vpn-monitor")
SRC=ROOT/"geo-independent-v23-candidate.py"
SHA="9e22a9b68a2e0fd5b1e66499778662419bc56cd8af491f229401269be2456ecd"
LOCK=Path("/opt/tmp/xray-update.lock")
LOGS=(Path("/opt/tmp/vpn-monitoring-lab/vpn-health.log"),Path("/opt/var/log/vpn-openai-health.log"))
FILES=[Path("/opt/etc/xray")/n for n in ("config.json","config.pending.json","config.lastgood.autoapply.json")]+[Path("/opt/bin/xray-update-v23.py"),Path("/opt/bin/xray-safe-hourly.sh"),Path("/opt/etc/vpn-monitor/dynamic-source-pins.json")]
ROUTES=(("v4rule",("rule","show")),("v4route",("route","show","table","all")),("v6rule",("-6","rule","show")),("v6route",("-6","route","show","table","all")))

def require(condition,reason):
    if not condition: raise RuntimeError(reason)

def sha(b):return hashlib.sha256(b).hexdigest()
def cmd(*args):return subprocess.check_output(args,stderr=subprocess.DEVNULL,timeout=3)

def witness():
    processes=[]
    for p in Path("/proc").glob("[0-9]*"):
        try:
            a=(p/"cmdline").read_bytes().split(bytes([0]))
            if a and a[0].endswith(b"/xray"):
                processes.append((p.name,(p/"stat").read_text().rsplit(")",1)[1].split()[19],b"/opt/etc/xray/config.json" in a))
        except OSError:pass
    firewall=[sha(b"\n".join(re.sub(rb"\[[0-9]+:[0-9]+\]",b"[c]",l) for l in cmd(n).splitlines() if not l.startswith(b"#"))) for n in ("iptables-save","ip6tables-save")]
    routes={k:cmd("ip",*a).decode().splitlines() for k,a in ROUTES}
    return sorted(processes),[sha(p.read_bytes()) if p.is_file() else None for p in FILES],firewall,routes

def route_diff(a,b):
    ok=True
    for k in a:
        removed=list((collections.Counter(a[k])-collections.Counter(b[k])).elements())
        added=list((collections.Counter(b[k])-collections.Counter(a[k])).elements())
        def shape(lines):
            return list(collections.Counter(tuple(w for w in ("expires","cache","proto","via","table","dev","linkdown") if w in l.split()) for l in lines).items())
        exact=a[k]==b[k]
        print("ROUTE",k,len(a[k]),len(b[k]),"exact",exact,"same_multiset",not removed and not added,
              "removed",len(removed),"added",len(added),"removed_shapes",shape(removed),"added_shapes",shape(added),flush=True)
        ok=ok and exact
    return ok

def quiet():
    minute=time.localtime().tm_min%15
    ages=[round(time.time()-p.stat().st_mtime) if p.is_file() else None for p in LOGS]
    print("PREFLIGHT",time.strftime("%H:%M:%S"),"minute",minute,"log_ages",ages,flush=True)
    require(3<=minute<=9,"outside quiet window")
    require(all(a is not None and 60<=a<=700 for a in ages),"collector quiet window not established")

def main():
    start=time.monotonic()
    quiet()
    st=SRC.lstat()
    require(stat.S_ISREG(st.st_mode) and st.st_uid==0 and not st.st_mode&0o022,"unsafe staging file")
    require(sha(SRC.read_bytes())==SHA,"staging SHA mismatch")
    with os.fdopen(os.open(LOCK,os.O_RDONLY|os.O_NOFOLLOW),"rb") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        quiet()
        before=witness()
        require(len(before[0])==1 and before[0][0][2],"other Xray process")
        spec=importlib.util.spec_from_file_location("geo_candidate",SRC)
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        original=m.probe_node
        count=[0]
        def guarded(ob):
            if time.monotonic()-start+55+30+5>=179:
                print("TRANSPORT_BUDGET_ABORT",count[0],round(time.monotonic()-start,2),flush=True)
                raise m.CleanupError("transport budget")
            result=original(ob);count[0]+=1
            return result
        m.probe_node=guarded
        try:
            with tempfile.TemporaryDirectory(dir=ROOT,prefix="geo-v23-trial-") as td:
                output=Path(td)/"candidate.json"
                sys.argv=[str(SRC),"--output",str(output)]
                m.main()
                d=json.loads(output.read_text())
                tags=[o["tag"] for o in d["outbounds"] if o.get("protocol")=="vless"]
                require(output.stat().st_mode&511==384 and bool(tags),"candidate invalid")
                print("COMPLETE",count[0],tags,flush=True)
        finally:
            after=witness()
            ok=route_diff(before[3],after[3])
            print("WITNESS","process",before[0]==after[0],"files",before[1]==after[1],"firewall",before[2]==after[2],"routes",ok,"seconds",round(time.monotonic()-start,2),flush=True)
            require(before[:3]==after[:3] and ok,"production witness changed")

if __name__=="__main__":
    try:main()
    except Exception as exc:
        # Only known local gate reasons, never arbitrary exception text.
        print("TRIAL_ABORT",type(exc).__name__,flush=True)
        raise SystemExit(1)
