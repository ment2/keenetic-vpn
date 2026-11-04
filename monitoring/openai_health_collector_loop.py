"""Independent 15-minute OpenAI reachability monitor, one isolated Xray at a time.

Offline staged only; does not auto-install on a router or change live Xray.
Secrets are read exclusively on router during explicit local --publish.
"""
import argparse
import fcntl
import json
import os
import signal
import time
from pathlib import Path
from monitoring.vpn_inventory import inventory
from monitoring.openai_node_probe import load_probe, probe_one
from monitoring.mqtt_lan_publisher import publish_once, load_password
from monitoring.openai_health_discovery import publish_for_inventory

HOST = "192.168.0.169"
TOPIC = "keenetic/vpn-monitor/v1/{node_id}/openai_http"


def one_round(config, probe, *, publish=False, password=None, sink=None):
    results = []
    for entry in inventory(config):
        tag = entry["tag"]
        try:
            event = probe_one(config, tag, probe)
            if publish:
                if not password:
                    raise ValueError("missing local MQTT password")
                publish_once(host=HOST,port=1883,username="keenetic_monitor",
                    password=password,topic=TOPIC.format(node_id=event["node_id"]),
                    payload=event,client_id="keenetic-vpn-openai")
            if sink is not None:
                sink.write(json.dumps(event, separators=(",",":")) + "\n")
                sink.flush()
            results.append((tag,event["status"]))
        except Exception as exc:
            results.append((tag,"error:"+type(exc).__name__))
    return results


def monitor(*, interval_s=900,max_cycles=0,publish=False,
            config_path="/opt/etc/xray/config.json",
            history_dir="/opt/var/lib/vpn-monitor/openai"):
    if not 300 <= interval_s <= 86400 or max_cycles < 0:
        raise ValueError("unsafe interval/cycles")
    directory=Path(history_dir)
    directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    os.chmod(directory,0o700)
    with os.fdopen(os.open(directory/"openai.lock",os.O_RDWR|os.O_CREAT,0o600),"r+") as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        stop=[False]
        def shutdown(sig,frame):stop[0]=True
        old_term=signal.signal(signal.SIGTERM,shutdown)
        old_int=signal.signal(signal.SIGINT,shutdown)
        try:
            probe=load_probe()
            count=0
            while not stop[0]:
                started=time.monotonic()
                try:
                    config=json.loads(Path(config_path).read_text())
                    entries=inventory(config)
                    password=load_password("/opt/etc/vpn-monitor/mqtt-password") if publish else None
                    if publish and count==0:
                        publish_for_inventory(entries=entries,host=HOST,
                            username="keenetic_monitor",password=password)
                    with os.fdopen(os.open(directory/"history.jsonl",os.O_WRONLY|os.O_APPEND|os.O_CREAT,0o600),"a") as sink:
                        statuses=one_round(config,probe,publish=publish,password=password,sink=sink)
                    print("OPENAI_CYCLE",count+1,statuses,flush=True)
                except Exception as exc:
                    print("OPENAI_CYCLE_FAILED",count+1,type(exc).__name__,flush=True)
                count+=1
                if max_cycles and count>=max_cycles: break
                while not stop[0] and time.monotonic()-started<interval_s:
                    time.sleep(1)
        finally:
            signal.signal(signal.SIGTERM,old_term)
            signal.signal(signal.SIGINT,old_int)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--interval",type=int,default=900)
    p.add_argument("--max-cycles",type=int,default=0)
    p.add_argument("--publish",action="store_true")
    a=p.parse_args()
    monitor(interval_s=a.interval,max_cycles=a.max_cycles,publish=a.publish)


if __name__=="__main__": main()
