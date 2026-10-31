"""RC31 offline evidence/falsification only: seven *versioned* legacy actors.

This is deliberately not a live fence, process enumerator, privileged executor,
release authorizer, or rescue installer. The recorded Linux4.9 cgroup-v1 root
escape remains a physical hard blocker independent of any software assertion.
"""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import re

ROOT=Path(__file__).resolve().parents[2]
SOURCES={
 "S97xray": "xray/production/opt/etc/init.d/S97xray",
 "S98xray-wifi": "xray/production/opt/etc/init.d/S98xray-wifi",
 "S99xray-watchdog": "xray/production/opt/etc/init.d/S99xray-watchdog",
 "xray-watchdog.sh": "xray/production/opt/bin/xray-watchdog.sh",
 "xray-wifi-rules.sh": "xray/production/opt/bin/xray-wifi-rules.sh",
 "xray-fc-cron-guard.sh": "xray/production/opt/bin/xray-fc-cron-guard.sh",
 "xray-safe-hourly.sh": "xray/production/opt/bin/xray-safe-hourly.sh",
}
ROOT_ESCAPE_OBSERVED="ROOT_CGROUP_V1_ESCAPE_OBSERVED_RC11"
UUID=re.compile(r"^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$")

@dataclass(frozen=True)
class ProcessWitness:
    pid:int
    ppid:int
    start_ticks:int
    boot_id:str
    executable_sha256:str
    generation:int
    cgroup:str
    privileged:bool
    socket_inodes:tuple=()

@dataclass(frozen=True)
class PhysicalEvidence:
    physical_vendor_kernel_boot_proven:bool=False
    all_seven_root_entrypoints_inhibited_preboot:bool=False
    complete_root_descendants_and_socket_scan_proven:bool=False
    independent_kernel_enforced_fencing_proven:bool=False
    durable_generation_cas_rollback_proven:bool=False
    physical_usb_removed_rescue_boot_proven:bool=False
    original_five_sha256_restored_after_power_loss:bool=False
    kernel_root_escape_contained_on_vendor_hardware:bool=False

def _shell_instructions(src):
    # Do NOT count text in comments as executed fencing. A line containing
    # flock alone is also not proof of its cross-process ownership.
    return [s.strip() for s in src.splitlines()
            if s.strip() and not s.lstrip().startswith("#")]

def evaluate(root=ROOT, *, expected_hashes=None, boot_id="", generation=0,
             before=(), after=(), physical=None):
    physical=physical or PhysicalEvidence()
    reasons=[ROOT_ESCAPE_OBSERVED]
    audit={}
    if set(SOURCES)!={
      "S97xray","S98xray-wifi","S99xray-watchdog","xray-watchdog.sh",
      "xray-wifi-rules.sh","xray-fc-cron-guard.sh","xray-safe-hourly.sh"}:
        reasons.append("SEVEN_ACTORS_MISSING_OR_CHANGED")
    if expected_hashes is None or set(expected_hashes)!=set(SOURCES):
        reasons.append("ACTOR_HASH_INVENTORY_UNSEALED")
    for actor,path in SOURCES.items():
        file=Path(root)/path
        if not file.is_file():
            reasons.append("MISSING_VERSIONED_ACTOR:"+actor)
            audit[actor]={"available":False}
            continue
        body=file.read_bytes()
        digest=hashlib.sha256(body).hexdigest()
        lines=_shell_instructions(body.decode("utf-8",errors="replace"))
        audit[actor]={"available":True,"source_sha256":digest}
        if not expected_hashes or expected_hashes.get(actor)!=digest:
            reasons.append("SNAPSHOT_SHA_MISSING_OR_DRIFTED:"+actor)
        # Even actual flock shell operations would not fence root children
        # that ignore the protocol, nor restart paths in another generation.
        if not any(re.search(r"(^|[; ]|\t)flock[ \t]+-[xn]",line) for line in lines):
            reasons.append("NO_EXECUTED_FLOCK_ACQUISITION:"+actor)
        reasons.append("NO_VERIFIED_SHARED_CAS_AND_PID_STARTTICKS:"+actor)
    if not UUID.fullmatch(boot_id or ""):
        reasons.append("BOOT_ID_UNVERIFIED")
    if generation<1:
        reasons.append("DURABLE_GENERATION_UNVERIFIED")
    seen_by_pid={}
    for phase,processes in (("BEFORE",before),("AFTER",after)):
        sockets=set()
        for p in processes:
            ident=(p.boot_id,p.start_ticks,p.executable_sha256,p.generation)
            if (p.pid<=1 or p.ppid<=1 or p.start_ticks<=0 or
                not UUID.fullmatch(p.boot_id or "") or
                not re.fullmatch(r"[0-9a-f]{64}",p.executable_sha256) or
                p.boot_id!=boot_id):
                reasons.append(phase+"_PID_START_BOOT_EXE_INVALID")
            if p.generation!=generation:
                reasons.append(phase+"_GENERATION_CAS_MISMATCH")
            if p.privileged or not p.cgroup or p.cgroup=="/":
                reasons.append(phase+"_ROOT_OR_UNFENCED_CGROUP")
            if p.pid in seen_by_pid and seen_by_pid[p.pid]!=ident:
                reasons.append(phase+"_PID_REUSE_OR_STARTTICKS_CHANGED")
            seen_by_pid[p.pid]=ident
            for inode in p.socket_inodes:
                if inode<=0 or inode in sockets:
                    reasons.append(phase+"_SOCKET_INODE_UNTRUSTED")
                sockets.add(inode)
        if phase=="AFTER" and processes:
            reasons.append("LIVE_LEGACY_DESCENDANTS_OR_ORPHANS_REMAIN")
    for key,val in vars(physical).items():
        if val is not True:
            reasons.append("PHYSICAL_HARD_NO_GO:"+key)
    reasons+=["NO_ROUTER_PROCESS_OR_CHILD_IDENTITY_READBACK",
              "NO_LIVE_ROOT_EGRESS_SOCKET_FENCING",
              "NO_PHYSICAL_INDEPENDENT_RESCUE_ACCEPTANCE"]
    return {
        "decision":"HARD_NO_GO_PRODUCTION",
        "reasons":tuple(sorted(set(reasons))),
        "source_snapshots":audit,
        "snapshot_count":sum(x["available"] for x in audit.values()),
        "live_fencing_proven":False,
        "hardware_accepted":False,
        "production_authorized":False,
        "router_actions":(),
    }

def snapshot_hashes(root=ROOT):
    return {a:hashlib.sha256((Path(root)/p).read_bytes()).hexdigest()
            for a,p in SOURCES.items() if (Path(root)/p).is_file()}
