"""Conservative per-VLESS health monitoring loop (15-minute cadence).

Executes one isolated test Xray at a time. Requires operator-local invocation
if --publish; remote agents must never read the MQTT password.
"""
import argparse
import fcntl
import json
import os
import signal
import time
from datetime import datetime,timezone
from pathlib import Path
from monitoring.vpn_inventory import inventory
from monitoring.vpn_node_probe import load_probe, probe_one
from monitoring.mqtt_lan_publisher import publish_once,load_password

def one_round(config, probe, publish=False, password=None, sink=None):
    results=[]
    for entry in inventory(config):
        tag=entry["tag"]
        try:
            event=probe_one(config,tag,probe)
            if publish:
                if not password:raise ValueError("password unavailable")
                publish_once(
                    host="192.168.0.169",port=1883,
                    username="keenetic_monitor",password=password,
                    topic=f"keenetic/vpn-monitor/v1/{entry['node_id']}/health",
                    payload=event,client_id="keenetic-vpn-health")
            if sink is not None:
                sink.write(json.dumps(event,separators=(",",":"))+"\n")
                sink.flush()
            results.append((tag,event["status"]))
        except Exception as exc:
            # The error type alone is printed. Never include exception details.
            results.append((tag,"error:"+type(exc).__name__))
    return results

def monitor(*, interval_s=900, max_cycles=0, publish=False,
            config_path="/opt/etc/xray/config.json",
            history_dir="/opt/var/lib/vpn-monitor/health"):
    if not 300 <= interval_s <= 86400 or max_cycles < 0:
        raise ValueError("unsafe interval/cycles")
    directory=Path(history_dir)
    directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    os.chmod(directory,0o700)
    with os.fdopen(os.open(directory/"health.lock",os.O_RDWR|os.O_CREAT,0o600),"r+") as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        stop=[False]
        def shutdown(signum,frame):stop[0]=True
        orig_term=signal.signal(signal.SIGTERM,shutdown)
        orig_int=signal.signal(signal.SIGINT,shutdown)
        try:
            probe=load_probe()
            cycles=0
            while not stop[0]:
                started=time.monotonic()
                try:
                    config=json.loads(Path(config_path).read_text())
                    password=load_password("/opt/etc/vpn-monitor/mqtt-password") if publish else None
                    with os.fdopen(os.open(directory/"history.jsonl",os.O_WRONLY|os.O_APPEND|os.O_CREAT,0o600),"a") as sink:
                        statuses=one_round(config,probe,publish,password,sink)
                    print("HEALTH_CYCLE",cycles+1,statuses,flush=True)
                except Exception as exc:
                    print("HEALTH_CYCLE_FAILED",cycles+1,type(exc).__name__,flush=True)
                cycles+=1
                if max_cycles and cycles>=max_cycles:break
                while not stop[0] and time.monotonic()-started < interval_s:
                    time.sleep(1)
        finally:
            signal.signal(signal.SIGTERM,orig_term)
            signal.signal(signal.SIGINT,orig_int)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--interval",type=int,default=900)
    p.add_argument("--max-cycles",type=int,default=0)
    p.add_argument("--publish",action="store_true")
    args=p.parse_args()
    monitor(interval_s=args.interval,max_cycles=args.max_cycles,publish=args.publish)

if __name__=="__main__":main()
