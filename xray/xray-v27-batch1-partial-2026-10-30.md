# Keenetic Xray v27 — batch 1 partial results

Date: 2026-10-30. Goal: seamless VPN pool replacement with no Xray restart or existing-connection loss.

## Five existing read_file jobs (not resubmitted)
- d290b026-126a-4e3e-8b1e-2bb9b02f3843 `/opt/bin/xray-control-v24.py`: queued.
- 9da27fcb-67ed-4608-8c22-535514256bba `/opt/bin/xray-watchdog-v25.sh`: done, exit_code 0, truncated false.
- 47e7b90b-80f1-4556-bc7a-4492e150fd8e `/opt/bin/xray-watchdog-switch-v26.py`: running.
- 1fb911ca-c181-4122-8b47-778603220d92 `/opt/etc/init.d/S97xray`: done, exit_code 0, truncated false.
- 4c4c43dd-4758-4a75-b556-2cf299acb714 `/opt/etc/init.d/S99xray-watchdog`: queued.

## Confirmed source analysis
`S97xray` uses `killall xray` in `stop_xray`; `restart` invokes this stop followed by start. It waits for local TCP listener 127.0.0.1:10808 to disappear (up to 10 seconds). This is not seamless and could kill a second Xray instance in blue-green deployment. Its `start` launches `/opt/sbin/xray run -config /opt/etc/xray/config.json` if listener absent.

`xray-watchdog-v25.sh` checks `/opt/bin/python3 /opt/bin/xray-control-v24.py status` and TCP listener 127.0.0.1:10808 every 30 seconds, logs state changes to `/opt/tmp/xray-watchdog-v25.log`. It does not restart Xray.

## Next step
Recheck only the five existing job IDs. Do not enqueue a new batch until these are done and analyzed. Then investigate subscription updater, config.pending.json and pool selector with up to five new read-only tasks. No changes to router services, files, routes, cron or kill-switch. Final deployed versions of modified files must be archived to `/Keenetic/Xray/` with hashes and rollback documentation.