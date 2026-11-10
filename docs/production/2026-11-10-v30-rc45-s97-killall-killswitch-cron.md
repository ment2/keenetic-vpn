# RC45: read-only S97 killall, kill-switch chain and cron writers

Date: 2026-11-10. Repository ment2/keenetic-vpn, feature/xray-v30-stable-tcp-ingress-lab-20261031.

Existing Keenetic read-only task `a3e6623e-4044-479b-baf2-c4b3da3f4fb8` completed `done`, `exit_code=0`; it was not resubmitted.

## Confirmed script excerpts
- `/opt/bin/xray-ks-home.sh` uses `/opt/sbin/iptables` and chain `XRAY_KS_HOME`. Observed `iptables -I` for an exclusion to `192.168.0.0/16`, `DROP` for `br0` source `192.168.1.0/24`, and `iptables -I FORWARD 1 -j XRAY_KS_HOME`. Only grep-selected lines were read, so full ordering, idempotence and actual packet-path enforcement require further verification. A watcher invokes this script every 15 seconds.
- `/opt/etc/init.d/S97xray` defines `stop_xray` using `killall xray` (line 12). Its `restart` branch calls `stop_xray` (line 39). Therefore the existing watchdog's `S97xray restart` can kill multiple Xray instances, including a future parallel candidate, unless independently fenced.
- Root cron line 28: every 15 minutes `/opt/bin/flock -n /opt/tmp/xray-update.lock /opt/bin/xray-safe-hourly.sh`, logging to `/opt/var/log/xray-update.log`.
- Root cron line 31: every 15 minutes a one-cycle `monitoring.openai_health_collector_loop --max-cycles 1 --publish`. Its write effects on the VPN configuration are not established by this job.

## Refined fencing and rollback gates (not executed)
1. Read complete `xray-ks-home.sh` and S97 stop/start paths; verify chain ordering and fail-closed under unchanged production state. Read only relevant control-flow portions of `xray-safe-hourly.sh` and OpenAI health collector to distinguish writer from observer. Do not print credentials/config payloads.
2. Record fresh boot ID, chain and routing baseline, PID/start_ticks, process descendants, S97/S98/S99/watchdog/cron state and updater lock ownership immediately before any separately approved maintenance.
3. Ensure an exclusive, time-bounded maintenance owner prevents S98 chain flush/rebuild, watchdog->S97 `killall xray`, and cron updater from racing with a dual-Xray cutover; preserve independent kill-switch enforcement and recovery. Do not use global killall or flush operations as fencing.
4. Only after separate exact-command approval and module target registration proof, execute two scoped TCP/UDP TPROXY rules with rollback of transaction-owned changes only. Verify fail-closed and no-leak before and after restoring supervisors. Never blindly run legacy S97 restart with two instances.
5. Same-USB backup integrity and isolated extraction verified; off-USB recovery deferred. A complete physical rollback rehearsal remains unverified.

**Decision: HARD NO-GO** for production module loads, firewall/routes/cron/service changes and API cutover. No physical write in this job.
