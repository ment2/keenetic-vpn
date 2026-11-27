# RC2 monitoring — live schedule reconciliation, 2026-11-27

Scope: monitoring only. geo-independent v23 work stopped. No VPN updater,
Xray, watchdog, firewall, routing or kill-switch modifications made by this
reconciliation.

## Live evidence (MSK)
- Job 6c1d7135-7d72-42fa-a991-2d8f7a01e685 DONE exit 0.
  At 19:12:14 actual cron contains RC2 probe at 3,18,33,48 and publish
  every minute, both umask 077, staged /opt/var/lib/vpn-monitor/rc2-stage.
  Cron installer comment identifies installation 19:08:12 and backup
  /opt/var/lib/vpn-monitor/rc2-cutover-backup-1795795689.
  Old OpenAI cron absent; old VLESS collector absent; traffic collector
  PID 746 remains. Existing Xray updater cron unchanged.
- Earlier alternate cutover job 7632be01-fe0c-4a15-b51a-ab1bc683b53d
  rejected stale init hash BEFORE writes; do not retry. The actual
  already-installed schedule uses direct rc2_cycle commands, not the
  separately staged rc2_schedule.py launcher. No need to replace it.
- Job 42bbe22a-7ff7-4275-ad1f-25ebd6c8db8c DONE: at 19:13:14
  publish log age 10 s, RC2_SNAPSHOT ok 10, RC2_CYCLE publish 0.
  Probe log absent (first scheduled quarter-hour still ahead).
- HA job db954a55-3de0-4c7b-9e5d-3fa10a1aa08f DONE:
  entity sensor.keenetic_dynamic_vpn_rc2 state ok, count 10, complete 8,
  last_updated 16:13:08 UTC, payload age 41 s. Complete means four
  fresh observations, not the number of qualified or active servers.
- HA job c54acbfc-3c5a-4565-8c01-a34ff8f2a3f7 DONE: existing dashboard
  vpn-monitor, rc2-shadow view unique, seven cards. No new UI change.
- Backup job d39c6d33-3222-47a2-ab4e-006672906981 DONE: all four
  SHA256SUMS entries match (init.before, cron.before, init.after,
  cron.after); init.after equals live init; all unrelated cron
  command lines identical in order. Actual installed cron SHA256
  ba1903a998c4b707551e93667d481c1d36744ce00d18af07effcda6cf29541d0.
  Existing backup verified, no live rollback needed or exercised.

## Current conclusion
Schedule installed and minute MQTT publication and HA ingestion confirmed.
Current dashboard: http://192.168.0.169:8123/vpn-monitor/rc2-shadow .
First scheduled probe at 19:18, second at 19:33; results not yet observed.
Logs are overwritten per run (bounded by one run, not full history).
Use HA recorder subscription_at/observations timestamps to distinguish
two actual scheduled generations, and current router probe/publish log.
Do not start duplicate manual probe, change schedules or claim two cycles
before evidence. Full physical iPhone visual not inspected in this turn.
If probe skipped due updater lock, report it honestly; do not modify VPN.
