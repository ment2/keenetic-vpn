# Keenetic traffic collector: manual activation and rollback (2026-11-04)

Scope: isolated monitoring process only, never modifies Xray/legacy S97/S98/S99/watchdog/cron/firewall/routes. Home Assistant MQTT integration is online and the owner already confirmed `HA_DISCOVERY_PUBACK_OK 12` and two successful three-interface traffic publications using a locally stored secret.

## Current state
Code is staged on Keenetic at `/opt/tmp/vpn-monitoring-lab/monitoring/`. Dry-run on interface apclii0 returned baseline then ok. All 33 offline tests passed on the router, task `3c9776b8-e15b-465a-92bb-53f253e4126a`, exit 0. Source is in `feature/vpn-monitoring-home-assistant-20261104`.

## Operator-local activation via Termius
The remote assistant connector MUST NOT run a command that reads `/opt/etc/vpn-monitor/mqtt-password` (prior attempt blocked). User runs the following locally when ready:

```sh
cd /opt/tmp/vpn-monitoring-lab || exit 1
umask 077
nohup /opt/bin/python3 -u -m monitoring.traffic_collector_loop --interval 60 --publish > /opt/tmp/vpn-monitoring-lab/collector.log 2>&1 < /dev/null &
echo "COLLECTOR_PID=$!"
sleep 3
tail -n 5 /opt/tmp/vpn-monitoring-lab/collector.log
```

Expected: `CYCLE_OK 1` with three interfaces; next every 60 seconds. When previous snapshots are old (>600s), first interval may be `gap`; steady state then `ok`. On error: `CYCLE_FAILED` records exception CLASS only (no secret values). The script uses private lock at `/opt/var/lib/vpn-monitor/collector.lock` and state files in `/opt/var/lib/vpn-monitor/traffic/`. A second run stops with `collector already running`.

## Status and stopping
```sh
ps | grep '[t]raffic_collector_loop'
tail -n 15 /opt/tmp/vpn-monitoring-lab/collector.log
```

To stop, identify the exact Python process running `monitoring.traffic_collector_loop`, then `kill <pid>`. **Never** run killall/python-wide termination. No router restart required.

This is an opt-in foreground process started via nohup. It does **not** auto-start on reboot. On reboot `/opt/tmp` may be lost; persist/install only in a separate reviewed step. Do not install cron or modify watchdog without explicit separate approval.

## HA
Discovery configs are retained at `homeassistant/sensor/keenetic6059_*/config`. MQTT interface state is non-retained under `keenetic/vpn-monitor/v1/traffic/{apclii0,br0,br1}`. Confirm one new `Keenetic VPN Monitoring` device with 12 sensors after activation. If entity registration fails, check HA MQTT integration diagnostics; avoid changing the integration account or publishing to unrelated topics.

Counters are measured at interfaces, not solely Xray, so avoid adding overlapping bridge/Wi-Fi bytes as independent totals. TLS not used by explicit owner consent for protected home Wi-Fi.
