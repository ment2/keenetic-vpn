# RC45: verified S98 loop, destructive XRAY_WIFI rebuild and fencing gates

Date: 2026-11-10. Branch `feature/xray-v30-stable-tcp-ingress-lab-20261031`.

Existing Keenetic Mobile read-only job `d6aa6105-6e17-4ad1-b31e-ec270970d31b` completed `done`, `exit_code=0`, without resubmission.

## Exact S98 behavior
`/opt/etc/init.d/S98xray-wifi` uses PID file `/opt/var/run/xray-wifi.pid`. On `start`, a live PID in that file causes an early exit. Otherwise a background subshell runs a `while true` loop and sleeps 60 seconds. The loop invokes `/opt/bin/xray-wifi-rules.sh` when any of these conditions fail: TCP PREROUTING jump to XRAY_WIFI for `192.168.1.0/24` on `br0`, corresponding UDP jump, any TPROXY appearance in `iptables -t mangle -L XRAY_WIFI -n`, or `local default` in routing table 100. Logs go to `/opt/var/log/xray-wifi.log`. `stop` kills the PID in the file and removes that file; `restart` calls stop then start. Stop semantics alone do not prove descendant fencing.

## Exact rules-script behavior
`/opt/bin/xray-wifi-rules.sh` checks/adds `fwmark 0x40000000/0x40000000 lookup 100 priority 20000`; performs `ip route replace local default dev lo table 100`; creates XRAY_WIFI if absent; then **flushes XRAY_WIFI** via `/opt/sbin/iptables -t mangle -F XRAY_WIFI`. It appends nine RETURN destination exclusions (`0/8`, `10/8`, `100.64/10`, `127/8`, `169.254/16`, `172.16/12`, `192.168/16`, `224/4`, `240/4`) and attempts TCP and UDP TPROXY on port 12345 with mark `0x40000000/0x40000000`; it checks/inserts corresponding PREROUTING jumps. No explicit `set -e` in the observed script. Failed TPROXY insertion can leave partial rules while the loop retries. **This is an active competing privileged writer, not a hypothetical one.**

## Watchdog and parent identities
`/opt/bin/xray-watchdog` does not exist. `/opt/bin/xray-watchdog.sh` exists, executable, 649 bytes; `/opt/bin/xray-ks-home-watch.sh` exists, mode 0700, 126 bytes. Actual watchdog script contents have not yet been inspected.

`/proc/PID/status` returned `PPid=1` for PID 719 (kill-switch watcher), 757 (S98), 776 (watchdog), 815 (Xray). Previous snapshot start ticks: 719/4471, 757/4495, 776/4506, 815/4570. Do not assume these PIDs or start ticks remain current.

## Refined fencing/rollback plan: not approved to execute
1. Obtain fresh boot ID, PID/start_ticks, process tree and child inventory, PID-file identity, S97/S98/S99/watchdog/cron start/respawn paths, exact chain/route snapshot, independent kill-switch health and recovery witness.
2. Prove an exclusive, bounded maintenance owner for XRAY_WIFI, including S98 background subshell, any in-flight `xray-wifi-rules.sh`, watchdog/cron restarts, and child processes. Stopping S98 alone is insufficient. **Do not disable the independent kill switch.**
3. Establish rollback and no-leak acceptance with pre/post checks, identity guards and time-bound recovery. No global iptables flush, no blanket `killall`, no unsafe full-tar restore.
4. Only after separate exact-command authorization, verify kernel module activation and target registration. If activation fails, no two-rule write.
5. Separately approve and transactionally insert precisely two TCP/UDP TPROXY rules after existing exclusions, with exact-match rollback. Validate packet-path and fail-closed, then restore controlled supervisors. Recheck chain after S98 resumes; S98's current rebuild behavior is a design blocker that must be reconciled before approval.

## Status
**HARD NO-GO** for module activation, production firewall/routes/cron/service modifications and API cutover. The backup is on the same USB and off-USB recovery remains deferred. No physical write was performed by this read-only job.
