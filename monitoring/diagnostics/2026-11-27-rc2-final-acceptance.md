# RC2 monitoring acceptance — 27 November 2026, 19:54 MSK

Scope: read-only acceptance. No manual probe, no change to VPN, monitoring schedule, dashboard, updater, watchdog, firewall, routes or kill-switch in this turn.

## Evidence
First-cycle report 4853e0f9a6cde1e9822336b39491af884eea8001 and checkpoint 59fd88cf376d5bf959dcce015758c74d772e0237 reopened.
First scheduled cycle: subscription 19:18:06, cache 19:19:46, exit 0 at 19:19:53; 10/10 results. First-cycle VPN/internet 5, OpenAI 3.
Second scheduled cycle: subscription 19:33:06, cache 19:34:38; all ten node observations 19:33:11–19:34:38; VPN/internet 6, OpenAI 5. Confirmed by HA history and current state, not by the overwritten second-cycle log.
Router job 9ffc483b-618d-4183-b3b0-7ce153bc3f8f DONE exit 0 at 19:53:10: cron SHA256 ba1903a998c4b707551e93667d481c1d36744ce00d18af07effcda6cf29541d0 and init SHA256 a14ac77c2f921736999d450e21ba492e31a9927db4d5fb1dee8d746a5eb27ef2 unchanged; probe schedule 03,18,33,48, publish each minute. Publish log 19:53:04 RC2_SNAPSHOT ok 10, RC2_CYCLE publish 0.
HA job 580d675a-775a-4bfd-9b8c-314e1ee9380e DONE exit 0 at 19:53:25: state ok, count 10, complete 10, publication age 22 s, subscription age 20m19s. Aggregate history 45 records with generations 19:10:21 (0/8 complete), 19:18:06 (8/10), 19:33:06 (10). All 60 history sensor mappings resolved. Internet duration history for every tag records both 19:19:56–57 and 19:34:49 MSK. Some unavailable intervals during rediscovery; no claim of uninterrupted numeric history. The freshness window allows 30-minute observations, so complete 10 is not evidence of a successful latest scheduled refresh.

| Node | Active at 19:53 | VPN | Internet ms/status | OpenAI | Geo |
|---|---|---|---|---|---|
| vpn01 | yes | ok | 1562 ok | ok | DE Berlin |
| vpn02 | no | not_confirmed | 2867 network_error | network_error | unknown |
| vpn03 | no | not_confirmed | 4065 timeout | timeout | unknown |
| vpn04 | no | ok | 3625 ok | ok | RU Saint Petersburg |
| vpn05 | no | not_confirmed | 2760 network_error | network_error | unknown |
| vpn06 | no | ok | 1508 ok | ok | NL Amsterdam |
| vpn07 | yes | ok | 2471 ok | ok | PL Warsaw |
| vpn08 | no | not_confirmed | 4066 timeout | timeout | unknown |
| vpn09 | yes | ok | 4160 ok | ok | US Washington |
| vpn10 | no | ok | 2724 ok | http_error | BY Minsk |

Durations include failed requests, not ICMP RTT. Geolocation refers to exit IP at observation time. No claim that membership at 19:53 equals membership at 19:33.

## Third cycle failure / exact mismatch
Latest probe log 19:48:04: SUBSCRIPTION_SNAPSHOT_FAILED ValueError; RC2_CYCLE probe 1. Snapshot and cache stayed at second generation. HA minute publication remains healthy but not a fresh probe.
Router job e0682bca-5511-4321-bd3b-36ebd06debe8 DONE exit 0 at 19:54:07. Pins file mode 0600. xray-update-v23.py modified 19:44:09, SHA256 b65fcb96dbc9dbdb81b5e06ba48a45adaf51cc77041634f4f5b5b0be26984041, does not match monitor pin; all three other source hashes match, all source files pass regular/owner/mode checks. Adapter verify_sources rejects mismatched SHA with ValueError before invoking subscription reader. This mismatch is a concrete blocker; the exact provenance/content of the changed updater has not been independently reviewed here. No pin changes or trust bypass. Do not roll back VPN to repair monitoring.

## Verdict
Two requested scheduled generations PASS; HA history and minute publication PASS. Continuous scheduled refresh FAIL since 19:48, overall monitoring acceptance conditional, not closed. Next step: independently review the exact changed updater and its subscription()/create_outbound contract, then separately update only monitor source pin if validated; verify next scheduled cycle. No updater modification, restart or repeated manual probe. UI native history graphs visually confirmed by user's 19:49 iPhone screenshot in prior turn; sorted configuration readback in job 44fcc2dd-a198-4a77-ac25-0ec513235cc4. No additional frontend inspection in this turn.
