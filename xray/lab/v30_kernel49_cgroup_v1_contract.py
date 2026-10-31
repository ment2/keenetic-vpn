#!/usr/bin/env python3
"""Offline cgroup v1 descendant-containment acceptance contract for Linux 4.9.

Never mounts, joins, creates, or writes cgroups. Purely consumes synthetic
/proc/cgroups, mountinfo, cgroup membership evidence, and two snapshots.
Mounting an existing cgroup does not mean membership was sealed before spawn.
All false positives are blocked and physical Keenetic proof remains false.
"""
import dataclasses
import json
from xray.lab.v30_sealed_descendant_inventory import evaluate, Snapshot

REQUIRED_CONTROLLERS = frozenset(("pids",))
# Cgroup v1 'pids' may not be built into actual Keenetic. A separate already
# mounted dedicated hierarchy is required, not just /proc cgroups listing.

def parse_proc_cgroups(value):
    out={}
    for line in value.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        columns=line.split()
        if len(columns)!=4:
            raise ValueError("incomplete /proc/cgroups")
        name,hierarchy,num,enabled=columns
        if name in out or not (hierarchy.isdecimal() and num.isdecimal()
                                and enabled in ("0","1")):
            raise ValueError("ambiguous cgroup hierarchy")
        out[name]={"hierarchy":int(hierarchy),"groups":int(num),
                   "enabled":enabled=="1"}
    return out

def parse_mounts(value):
    mounts=[]
    for line in value.splitlines():
        a,sep,b=line.partition(" - ")
        if not sep:
            raise ValueError("invalid mountinfo")
        left=a.split()
        right=b.split()
        if len(left)<6 or len(right)<3:
            raise ValueError("truncated mountinfo")
        if right[0]=="cgroup":
            mounts.append({"mount_id":left[0],"device":left[2],
                          "mount":left[4],"options":left[5].split(","),
                          "super_options":right[2].split(",")})
    return mounts

def inspect(v1_cgroups,mounts,*,scope,first,second,boot_guardian_outside_usb=False,
            scope_created_before_spawn=False,escape_impossible=False,
            legacy_spawners_fenced=False,all_proc_files_readable=False):
    reasons=[]
    try:
        controllers=parse_proc_cgroups(v1_cgroups)
        mounted=parse_mounts(mounts)
    except ValueError:
        controllers={}
        mounted=[]
        reasons.append("UNTRUSTED_KERNEL_CGROUP_DATA")
    pids=controllers.get("pids")
    if not pids or not pids["enabled"] or pids["hierarchy"]<=0:
        reasons.append("CGROUP_V1_PIDS_CONTROLLER_NOT_PROVEN")
    valid_mounts=[m for m in mounted if "pids" in m["super_options"]
                  and "ro" not in m["options"]]
    if len(valid_mounts)!=1:
        reasons.append("NO_UNIQUE_WRITABLE_PIDS_CGROUP_V1_MOUNT")
    if not isinstance(scope,str) or not scope.startswith("/") or ".." in scope.split("/"):
        reasons.append("UNTRUSTED_SCOPE_PATH")
    if scope_created_before_spawn is not True:
        reasons.append("SCOPE_NOT_ESTABLISHED_BEFORE_SPAWN")
    if escape_impossible is not True:
        reasons.append("SCOPE_ESCAPE_NOT_PREVENTED")
    if legacy_spawners_fenced is not True:
        reasons.append("UNFENCED_LEGACY_SPAWNER")
    if all_proc_files_readable is not True:
        reasons.append("INCOMPLETE_PROC_FD_CGROUP_AND_NET")
    if boot_guardian_outside_usb is not True:
        reasons.append("NO_NONUSB_BOOT_GUARDIAN")
    if not isinstance(first,Snapshot) or not isinstance(second,Snapshot):
        reasons.append("MISSING_TWO_MEMBER_SNAPSHOTS")
    else:
        a=evaluate(first,second)
        reasons.extend(a["reason_codes"])
        if a["scope"]!=scope:
            reasons.append("SCOPE_NOT_BOUND_TO_SNAPSHOT")
        if first.source!="SYNTHETIC" or second.source!="SYNTHETIC":
            reasons.append("EVIDENCE_FROM_UNAUTHORIZED_LIVE_SOURCE")
    return {
        "status":"NO_PRODUCTION_RECOVERY" if reasons else "OFFLINE_LOGICAL_CONTRACT_ONLY",
        "reason_codes":sorted(set(reasons)),
        "real_kernel49_cgroup_support_proven":False,
        "physical_descendant_containment_proven":False,
        "production_recovery_authorized":False,
        "router_commands":[]
    }

def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--offline",action="store_true")
    a=p.parse_args()
    if not a.offline:p.error("only --offline, no live cgroup commands")
    print(json.dumps(inspect("","",scope="/v30",first=None,second=None),sort_keys=True))

if __name__=="__main__":main()
