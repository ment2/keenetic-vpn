# 2026-11-04: nohup missing on Keenetic, corrected session launcher

Owner attempted approved 60-second MQTT monitoring via `nohup /opt/bin/python3 -u -m monitoring.traffic_collector_loop --interval 60 --publish`. Shell printed `-sh: nohup: not found`; shell job exited 127. PID 5594 referred to failed job, NOT a running collector.

Read-only router task 3351916d-4477-4595-97a4-6108d028a852 returned done exit 0: `ps | grep '[t]raffic_collector_loop'` produced no running collector; Python `subprocess.Popen(start_new_session=True)` available and `os.setsid` true; staged code `/opt/tmp/vpn-monitoring-lab/monitoring/traffic_collector_loop.py` exists and collector.log contained 22 bytes error. No production changes occurred.

Alternative operator-local launcher (do not remotely run from assistant; collector reads local private MQTT password):

```sh
cd /opt/tmp/vpn-monitoring-lab || exit 1
/opt/bin/python3 - <<'PY'
import os, subprocess, time
root = "/opt/tmp/vpn-monitoring-lab"
log = root + "/collector.log"
env = os.environ.copy()
env["PYTHONPATH"] = root
with open(log, "ab", buffering=0) as output:
    p = subprocess.Popen(
        ["/opt/bin/python3", "-u", "-m", "monitoring.traffic_collector_loop",
         "--interval", "60", "--publish"],
        cwd=root, env=env,
        stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
        start_new_session=True, close_fds=True
    )
print("COLLECTOR_PID", p.pid)
time.sleep(3)
print("PROCESS_RUNNING" if p.poll() is None else "PROCESS_EXIT", p.poll())
with open(log, "r", errors="replace") as stream:
    print("LOG_TAIL", "".join(stream.readlines()[-5:]))
PY
```

Expect `PROCESS_RUNNING` and `CYCLE_OK 1`. This runs independently of Termius but DOES NOT persist across router reboot, and may stop if filesystem in /opt/tmp disappears. Do not use shell nohup; no cron/S97/S98/S99/watchdog/firewall/routes/Xray changes. On shutdown, target only the exact collector PID after checking command identity; no killall.

Do not claim active monitoring until local launcher returns successfully and a second CYCLE_OK after ~60s is confirmed.
