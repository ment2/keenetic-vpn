# Geo RC1 acceptance — 2026-11-27 20:00 MSK
PARTIAL PASS. Existing MCP job 5e69c604-4016-442c-b8ad-345f3a7cf724 done, exit 0, snapshot 20:00:09. No new job or production changes.
Installed SHA256 b65fcb96dbc9dbdb81b5e06ba48a45adaf51cc77041634f4f5b5b0be26984041 matches. Backup exists, SHA256 00f08d13bd653ce72a57b0f73ec046f004dca1f900a36cfcec4d254dfa2392cf.
19:46:13 APPLY; 19:46:17 SUCCESS, internet and OpenAI verified. No rollback/SKIP shown in fresh cycle excerpt. Active vpn01/vpn07/vpn09, fallback vpn01. Ten candidates, three allowed, one excluded, six unverified.

|Tag|Updater status|Updater country|Cached RC2 geo|
|---|---|---|---|
|vpn01|ALLOWED|DE|DE 78.17.178.91|
|vpn02|UNVERIFIED|unknown|network_error|
|vpn03|UNVERIFIED|unknown|timeout|
|vpn04|UNVERIFIED|unknown|RU 178.72.144.171; exit_ip timeout|
|vpn05|UNVERIFIED|unknown|network_error|
|vpn06|UNVERIFIED|unknown|NL 82.24.91.21|
|vpn07|ALLOWED|PL|PL 140.225.214.63|
|vpn08|UNVERIFIED|unknown|timeout/network_error|
|vpn09|ALLOWED|US|US 152.53.242.98|
|vpn10|EXCLUDED_BY|BY|BY 46.243.183.2; OpenAI HTTP error|

BY live exclusion PASS. RU live exclusion NOT VERIFIED: vpn04 not admitted but no EXCLUDED_RU observed. No RU/BY among admitted tags on available evidence; not a fresh independent exit-IP test. RC2 freshness FAIL: cache mtime 19:34:38, probe exit 1, publish exit 0. HA fresh measurements not independently verified; prior reported 19:52 publication does not prove freshness. Full error/rollback history not available in excerpt. Next: read-only inspect RC2 probe failure and HA measurement timestamps/source pins; do not force updater or rollback. Incident 128.71.157.89 ROOT CAUSE UNCONFIRMED.
