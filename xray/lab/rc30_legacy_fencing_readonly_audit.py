"""RC30 read-only hardware-blocker audit for first TPROXY ingress migration.

Reads the versioned production script copies as untrusted snapshots; NO router
connection, shell commands or process signals. A PASS of this test means a
hard blocker was correctly detected, never that a legacy root actor was fenced.
"""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SNAPSHOTS={
 "S97xray":"xray/production/opt/etc/init.d/S97xray",
 "S98xray-wifi":"xray/production/opt/etc/init.d/S98xray-wifi",
 "S99xray-watchdog":"xray/production/opt/etc/init.d/S99xray-watchdog",
 "watchdog":"xray/production/opt/bin/xray-watchdog.sh",
 "cron-update":"xray/sources/xray-safe-hourly.LEGACY-library.sh",
}
def audit(root=ROOT):
    reasons=[]
    contents={}
    for actor,path in SNAPSHOTS.items():
        p=(root/path)
        if not p.is_file():
            reasons.append("MISSING_LEGACY_SOURCE:"+actor)
            continue
        contents[actor]=p.read_text(encoding="utf-8")
    if "killall xray" in contents.get("S97xray",""):
        reasons.append("S97_KILLALL_CAN_KILL_BOTH_INGRESS_OWNERS")
    if 'restart' in contents.get("watchdog","") and "S97xray" in contents.get("watchdog",""):
        reasons.append("ROOT_WATCHDOG_CAN_RESTART_S97_DURING_CUTOVER")
    if 'while true' in contents.get("S98xray-wifi","") and "xray-wifi-rules.sh" in contents.get("S98xray-wifi",""):
        reasons.append("S98_CAN_REWRITE_TPROXY_DURING_CUTOVER")
    if 'kill "$(cat "$PIDFILE")"' in contents.get("S99xray-watchdog",""):
        reasons.append("S99_PID_ONLY_STOP_NO_START_TICKS_OR_DESCENDANT_FENCE")
    if '"$SERVICE" stop' in contents.get("cron-update","") and '"$SERVICE" start' in contents.get("cron-update",""):
        reasons.append("CRON_SUBSCRIPTION_UPDATER_CAN_RESTART_LEGACY")
    for actor,body in contents.items():
        # Merely mentioning "flock" in a comment is NOT a live shared CAS
        # protocol. Require concrete exclusive acquisition AND generation
        # and PID/start-ticks identity evidence before considering a fence.
        if not (("flock -x" in body or "flock -n" in body)
                and "generation" in body and "start_ticks" in body):
            reasons.append("NO_SHARED_GENERATION_LOCK:"+actor)
    return {
        "decision":"HARD_NO_GO",
        "reasons":tuple(sorted(set(reasons+[
            "REAL_ROOT_CGROUP_ESCAPE_NOT_KERNEL_FENCED",
            "NO_PHYSICAL_CAS_PID_STARTTICKS_DESCENDANT_ACCEPTANCE",
            "NO_INDEPENDENT_USB_FREE_RESCUE",
            "NO_VERIFIED_GENERIC_UDP_FLOW_PINNING",
        ]))),
        "fencing_proven":False,
        "production_authorized":False,
        "router_actions":(),
    }
