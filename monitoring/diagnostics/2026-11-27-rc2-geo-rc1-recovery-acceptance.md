# RC2 monitor recovery — scheduled acceptance 2026-11-27 20:03 MSK

## Scope and baseline

Read-only verification after source-pin recovery at 20:00:19 MSK. Baseline report: commit 4bbb034d334e9967e3fd60078831a1c1258a1886, monitoring/diagnostics/2026-11-27-rc2-geo-rc1-pin-recovery.md. No configuration edits, manual probes, restarts or changes to VPN, Xray, updater, Geo RC1, firewall, routes, watchdog, kill-switch, cron or Home Assistant dashboard.

## Router evidence

Job 3026a150-ecd9-4e09-a9fe-738f953dc3f0 DONE exit 0, 20:04:11 MSK: subscription 10 entries at 20:03:06; probe was still in progress (previous cache 19:34:38). All four source pins matched. Geo RC1 updater remains SHA256 b65fcb96dbc9dbdb81b5e06ba48a45adaf51cc77041634f4f5b5b0be26984041. Active tags vpn01, vpn06, vpn07, vpn09.

Cron unchanged, SHA256 ba1903a998c4b707551e93667d481c1d36744ce00d18af07effcda6cf29541d0. Monitor init unchanged, SHA256 a14ac77c2f921736999d450e21ba492e31a9927db4d5fb1dee8d746a5eb27ef2. Probe minutes 03,18,33,48; publication every minute.

Job 62a4d00e-1d67-4653-a81c-562ddd3894c3 DONE exit 0, 20:05:07 MSK: subscription 20:03:06, probe cache 20:04:37, probe log 20:04:44. Log evidence: SUBSCRIPTION_SNAPSHOT 10; RC2_HISTORY 10 10; RC2_PROBE 10 10; RC2_CYCLE probe 0. Publication at 20:05:04: RC2_SNAPSHOT ok 10; RC2_CYCLE publish 0.

## Home Assistant evidence

Job 906e8b5c-e631-4810-9341-413da78597fa at 20:04:18 showed the new subscription but only 3/10 unexpired observations from the previous cycle. Not counted as new-cycle acceptance.

Job 863e96fd-f1a1-4ac2-aab9-cc2aa5c54ca4 DONE exit 0, 20:05:52 MSK: sensor.keenetic_dynamic_vpn_rc2 state ok, count 10, probe_complete 10, subscription_at 20:03:06, checked_at 20:05:03, publication age 49 seconds. All node observations belong to the new cycle (20:03:10–20:04:37 MSK).

| Node | Active | VPN | Internet | Duration ms | OpenAI | Geo |
|---|---|---|---|---:|---|---|
| vpn01 | yes | ok | ok | 1569 | ok | DE Berlin |
| vpn02 | no | not_confirmed | network_error | 2815 | network_error | network_error |
| vpn03 | no | not_confirmed | timeout | 4080 | timeout | timeout |
| vpn04 | no | not_confirmed | network_error | 3306 | network_error | network_error |
| vpn05 | no | not_confirmed | network_error | 2840 | network_error | network_error |
| vpn06 | yes | ok | ok | 2543 | ok | NL Amsterdam |
| vpn07 | yes | ok | ok | 1909 | ok | PL Warsaw |
| vpn08 | no | not_confirmed | timeout | 4094 | timeout | network_error |
| vpn09 | yes | ok | ok | 2214 | ok | US Washington |
| vpn10 | no | ok | ok | 1903 | http_error | BY Minsk |

Durations are recorded internet probe durations, not ICMP RTT; failed durations are not successful latency measurements. No endpoint addresses or credentials included. vpn10 is independently monitored even though it is outside the active pool. The four active nodes passed VPN, internet, OpenAI and geo probes. Five nodes passed VPN/internet; four passed OpenAI; five had confirmed geo.

## Verdict

PASS — first scheduled cycle after monitor-only source-pin recovery. End-to-end subscription refresh, ten-node probing/history publication and Home Assistant ingestion are confirmed. Individual failed node checks are monitoring results, not a monitoring pipeline failure. No manual cycle or configuration change was made during acceptance. Future cycles and independent graph rendering/history UI were not retested in this read-only acceptance. No claim of future-cycle success.
