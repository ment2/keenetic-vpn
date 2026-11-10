# RC45: watchdog restart loop, kill-switch watcher, S98 PID and boot identity

Date: 2026-11-10. Repository ment2/keenetic-vpn. Branch feature/xray-v30-stable-tcp-ingress-lab-20261031.

Existing read-only Keenetic Mobile task `191a227e-55fe-4593-9db0-63e1fcc90726` returned `done`, `exit_code=0` without resubmission.

## Verified exact control flow
- `/opt/bin/xray-watchdog.sh` checks `netstat -lnt` for listening `127.0.0.1:10808` every 30 seconds. On failure, it invokes `/opt/etc/init.d/S97xray restart`, sleeps 5 seconds, rechecks SOCKS5, and logs outcomes to `/opt/tmp/xray-watchdog.log`. The script is a privileged restart actor, not a passive observer.
- `/opt/bin/xray-ks-home-watch.sh` loops forever invoking `/opt/bin/xray-ks-home.sh` then sleeping 15 seconds. The called script was NOT read in this job, so its exact effects remain unverified.
- `/opt/var/run/xray-wifi.pid` contains `757`, consistent with prior S98 process PID 757, but this alone does not prove PID/start_ticks ownership.
- Current boot ID `17cc872c-36cb-4411-899e-9eec5f3155c9` matches earlier snapshot.

## Refined fencing and rollback prerequisites (NOT EXECUTED)
1. Inspect `S97xray` restart effects, actual `xray-ks-home.sh` contents, S99/cron/other re-spawners and descendants read-only, without leaking VPN credentials.
2. At maintenance start, recheck boot ID, PID/start_ticks and process ancestry, PID-file owner, mangle chain and routing snapshots, Xray health and fail-closed witnesses. Reject drift.
3. Establish a bounded, exclusive maintenance transaction that prevents both S98's periodic XRAY_WIFI flush/rebuild and watchdog's S97 restart from racing with module/rule changes; preserve independent kill-switch enforcement. Stop of a single parent PID is insufficient without descendant and respawn fencing.
4. Prepare separately approved, exact rollback commands for only transaction-owned firewall rules and service state, with no-leak checks before and after. Never blanket-flush tables or globally disable kill switch.
5. Physical module activation and precisely two TPROXY rules require separate owner approval and demonstrated registration. No live cutover until validated.

## Decision
**HARD NO-GO** for production writes and cutover. Same-USB backup and isolated restore were verified; independent off-USB recovery remains deferred. This job performed no writes or restarts.
