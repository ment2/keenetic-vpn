#!/usr/bin/env python3
"""Real disposable Linux cgroup-v1 pids/fork/exec/escape test.

Only run as root INSIDE A NEW MOUNT NAMESPACE on a GitHub runner.
Never touch host cgroup mounts, /opt, firewall, routes, cron, or Keenetic.
If pids cgroup v1 is unavailable (typical Ubuntu cgroup v2 host), EXIT 77
and write an explicit HARD_NO_GO capability result. Never pretend PASS.

A successful real inheritance test DOES NOT prove a sealed scope:
privileged descendants might migrate to a parent cgroup. We attempt this
in a private namespace and record either escape or denial with NO-GO.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from xray.staging.v30_supervisor_core import proc_stat

MODULE = "xray.lab.v30_rc6_cgroup_v1_lab"

def atomic_text(path, data):
    p=Path(path)
    p.write_text(data,encoding="utf-8")

def observe_members(scope):
    data=(scope/"cgroup.procs").read_text()
    return set(int(x) for x in data.split() if x.isdecimal())

def wait_for(path,seconds=8):
    end=time.monotonic()+seconds
    while not Path(path).exists():
        if time.monotonic()>=end:
            raise RuntimeError("missing bounded evidence: "+str(path))
        time.sleep(.03)

def report(root,**data):
    obj={"schema":1,"source":"ACTUAL_LINUX_PROCESSES_DISPOSABLE_RUNNER",
         "production_containment_proven":False,
         "keenetic_kernel49_verified":False,"router_commands":[],**data}
    (root/"result.json").write_text(json.dumps(obj,sort_keys=True,indent=2)+"\n")
    return obj

def no_capability(root, reason):
    data=report(root,status="CGROUP_V1_UNAVAILABLE",
                reason=reason,process_inheritance_tested=False,
                physical_containment_gate="HARD_NO_GO")
    print("CGROUP1: UNAVAILABLE "+reason+"; HARD_NO_GO (no false pass)",flush=True)
    return 77

def grandchild(root,base):
    root=Path(root)
    atomic_text(root/"grandchild-ready.json",json.dumps({
        "pid":os.getpid(),"ticks":proc_stat(os.getpid())[2],
        "ppid":os.getppid(),"session":os.getsid(0)}))
    wait_for(root/"escape-go",12)
    try:
        # This attempts the actual cgroup-v1 privilege escape, on the
        # disposable hierarchy only. It is NOT a production action.
        (Path(base)/"cgroup.procs").write_text(str(os.getpid())+"\n")
        outcome="ESCAPE_SUCCEEDED"
    except OSError as e:
        outcome="ESCAPE_DENIED_"+str(e.errno)
    atomic_text(root/"escape-result",outcome+"\n")
    wait_for(root/"release",12)

def forker(root,scope,base):
    root=Path(root)
    (Path(scope)/"cgroup.procs").write_text(str(os.getpid())+"\n")
    pid=os.fork()
    if pid==0:
        os.setsid()
        os.execv(sys.executable,[sys.executable,"-m",MODULE,
                                 "--grandchild",str(root),str(base)])
    atomic_text(root/"forker-ready.json",json.dumps({
        "pid":os.getpid(),"ticks":proc_stat(os.getpid())[2],
        "grandchild_pid":pid}))
    wait_for(root/"release",12)
    os.waitpid(pid,0)

def runner(root):
    root=Path(root).resolve()
    if not str(root).startswith(("/tmp/","/home/runner/work/")):
        raise RuntimeError("disposable-root only")
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    if os.geteuid()!=0:
        return no_capability(root,"requires root inside disposable mount namespace")
    status=Path("/proc/cgroups").read_text()
    enabled=[line.split() for line in status.splitlines()
             if line.strip() and not line.startswith("#")]
    if not any(len(x)==4 and x[0]=="pids" and x[3]=="1" for x in enabled):
        return no_capability(root,"pids controller absent/disabled")
    mount=root/"private-cgroup-v1"
    mount.mkdir(mode=0o700,exist_ok=False)
    cmd=subprocess.run(["mount","-t","cgroup","-o","pids","none",str(mount)],
                       capture_output=True,text=True,timeout=8)
    if cmd.returncode:
        return no_capability(root,"kernel denied isolated cgroup v1 mount: "+
                             cmd.stderr.strip()[:160])
    owner=None
    try:
        scope=mount/"v30-private-fork"
        scope.mkdir(mode=0o700)
        owner=subprocess.Popen([sys.executable,"-m",MODULE,"--forker",
                                str(root),str(scope),str(mount)],
                               stdin=subprocess.DEVNULL,start_new_session=True)
        wait_for(root/"forker-ready.json")
        wait_for(root/"grandchild-ready.json")
        p=json.loads((root/"forker-ready.json").read_text())
        g=json.loads((root/"grandchild-ready.json").read_text())
        if owner.pid!=p["pid"]:
            raise RuntimeError("forker PID mismatch")
        members=observe_members(scope)
        if not {p["pid"],g["pid"]}.issubset(members):
            raise RuntimeError("cgroup v1 fork/exec inheritance unverified")
        print("CGROUP1: REAL_FORK_EXEC_INHERITANCE_PASS",flush=True)
        atomic_text(root/"escape-go","GO\n")
        wait_for(root/"escape-result")
        escape=(root/"escape-result").read_text().strip()
        after=observe_members(scope)
        if escape=="ESCAPE_SUCCEEDED" and g["pid"] in after:
            raise RuntimeError("escape report contradicts membership")
        if escape.startswith("ESCAPE_DENIED_") and g["pid"] not in after:
            raise RuntimeError("denied escape but descendant absent")
        print("CGROUP1: REAL_PRIVILEGED_DESCENDANT_"+escape,flush=True)
        atomic_text(root/"release","DONE\n")
        owner.wait(timeout=8)
        if owner.returncode:
            raise RuntimeError("forker/grandchild failed")
        end=time.monotonic()+4
        while observe_members(scope):
            if time.monotonic()>end:
                raise RuntimeError("cgroup did not drain")
            time.sleep(.05)
        outcome=report(root,status="REAL_CGROUP_V1_FORK_EXEC_OBSERVED",
                       process_inheritance_tested=True,
                       privileged_escape=escape,
                       scope_sealed_proven=False,
                       physical_containment_gate="HARD_NO_GO")
        print("CGROUP1: REAL_SCOPE_DRAIN_PASS",flush=True)
        print("CGROUP1: HARD_NO_GO no verified containment of privileged descendants",flush=True)
        return 0
    finally:
        if owner and owner.poll() is None:
            atomic_text(root/"release","CLEANUP\n")
            try:owner.wait(timeout=4)
            except subprocess.TimeoutExpired:
                owner.kill()
                owner.wait(timeout=4)
        if (mount/"v30-private-fork").exists():
            try:(mount/"v30-private-fork").rmdir()
            except OSError:pass
        subprocess.run(["umount",str(mount)],capture_output=True,timeout=8)

def main():
    parser=argparse.ArgumentParser()
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--run",type=Path)
    mode.add_argument("--forker",nargs=3)
    mode.add_argument("--grandchild",nargs=2)
    args=parser.parse_args()
    if args.run:sys.exit(runner(args.run))
    if args.forker:forker(*args.forker)
    if args.grandchild:grandchild(*args.grandchild)

if __name__=="__main__":
    main()
