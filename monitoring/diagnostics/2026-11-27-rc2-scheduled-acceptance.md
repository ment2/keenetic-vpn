# RC2 scheduled acceptance — first cycle, 27 November 2026

Baseline b0421a96ea763d16586c3d03e1a2c27981a9ab9a.
Read-only acceptance, no production or monitoring configuration changes,
no manual probes or duplicate cutover.

## First scheduled cycle: PASS
Router job b4735c60-b9e2-4936-97df-28e7085a5d1c DONE exit 0.
At 19:22:08 MSK:
- Full subscription updated 19:18:06, 10 entries.
- Probe cache updated 19:19:46.
- Probe log 19:19:53: SUBSCRIPTION_SNAPSHOT 10; RC2_HISTORY 10 10;
  RC2_PROBE 10 10; RC2_CYCLE probe 0.
- Publish log 19:22:04: RC2_SNAPSHOT ok 10; RC2_CYCLE publish 0.
- Cron SHA256 ba1903a998c4b707551e93667d481c1d36744ce00d18af07effcda6cf29541d0
  and init SHA256 a14ac77c2f921736999d450e21ba492e31a9927db4d5fb1dee8d746a5eb27ef2
  unchanged from accepted schedule. Probe at 03,18,33,48; publish each minute.
- Active VPN pool count 3, not modified by acceptance.

## HA ingestion: PASS for current state
HA job 1d2f60e5-ecc4-4580-980a-6a3369834d92 DONE exit 0.
Current sensor.keenetic_dynamic_vpn_rc2 state ok, count 10, probe_complete 10,
subscription_at 1795796286, checked_at 1795796524, age 33 s.
Complete means fresh results, not ten reachable VPNs.
HA history API for aggregate sensor since 16:08 UTC returned only two rows;
one had subscription generation 19:10:21 MSK, checked at 19:11:04,
complete 0. No fresh observations in that historic row. This response does
not prove a second generation or full minute-by-minute history.
No recorder settings changed. Prior seven-card view verification retained.

## Pending second scheduled cycle
At last read 19:22 MSK, the 19:33 cycle has not yet occurred.
First cycle accepted, final two-cycle acceptance pending. Existing
one-time acceptance scheduled at 19:45 MSK; no additional manual
probe or duplicate automation needed. Use current router logs (overwrite
each run), this report's first-cycle evidence, and HA current state and
history to corroborate second generation. Report history limitations
honestly. VPN/updater/watchdog/firewall/routes/kill-switch unchanged.
