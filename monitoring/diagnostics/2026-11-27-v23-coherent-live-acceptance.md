# Geo-independent v23 — coherent live candidate acceptance, 27 November 2026

Production release remains HARD NO-GO. No production config, updater, pin,
cron, firewall, route, kill-switch or service changes requested or performed.

## Confirmed preflight and full trial
Previous job 7e743a97-b7e3-470d-8fed-d6bfa0a0ce77 completed exit 0.
At 18:21:07 MSK collector log ages 170 and 332 seconds, updater log 289.
Existing staged candidate and existing SHA-pinned acceptance harness reused.
Job de6c907e-805c-45c5-84ab-268c5e7c0de1 completed exit 0.
At 18:22:09 preflight before and after lock: collector ages 231 and 394
seconds, minute modulo 15 = 7. Single fresh subscription, ten entries.
Real Xray -test PASS, private output validated and removed with temporary
directory. Elapsed 92.7 s including witnesses. Four admitted, six unverified.

| Tag | Internet | OpenAI | Exit IP | Geo | Decision |
|---|---|---|---|---|---|
| vpn01 | ok | ok | ok | ok | ALLOWED |
| vpn02 | network_error | network_error | network_error | network_error | UNVERIFIED |
| vpn03 | timeout | timeout | timeout | timeout | UNVERIFIED |
| vpn04 | timeout | network_error | network_error | network_error | UNVERIFIED |
| vpn05 | network_error | network_error | network_error | network_error | UNVERIFIED |
| vpn06 | ok | ok | ok | ok | ALLOWED |
| vpn07 | ok | ok | ok | ok | ALLOWED |
| vpn08 | timeout | timeout | timeout | network_error | UNVERIFIED |
| vpn09 | ok | ok | ok | ok | ALLOWED |
| vpn10 | ok | http_error | ok | ok | UNVERIFIED |

Pool vpn01/vpn06/vpn07/vpn09, fallback vpn01. No exact non-401 HTTP code
recorded. This is a candidate, not an applied pool. No reuse of monitoring
cache. Earlier geo-only vpn04 regression remains valid; current vpn04 fails
mandatory probes independently of geography.

## Witnesses
Main Xray PID/start ticks/child inventory, active/pending/lastgood,
builder/wrapper/pins file digests, normalized IPv4 and IPv6 firewall
rules all matched before and after. Separate route snapshots:
IPv4 rules 6/6, IPv4 routes 90/90, IPv6 rules 2/2, IPv6 routes 66/66;
all exact and multiset equal, no additions/removals. Prior route mismatch
not reproduced; historical cause still unproven.

Read-only job 40051b22-0bc6-4faf-8ace-4b8c39744f8c completed exit 0.
IPv4 two TPROXY rules (one per TCP/UDP), two PREROUTING jumps, one mark
rule and one table 100 local default; XRAY_KS_HOME RETURN/DROP chain.
IPv6 no corresponding XRAY chain and no default route in all displayed
tables. Initial audit aggregated same-name chains across iptables tables:
do not infer filter policies or ordering from that output. Separate
filter/mangle audit and passive 65-second route observation job
ae50a45c-3d68-45b2-accf-3b4567a36621 completed exit 0. Exact separated
tables: IPv4 filter FORWARD policy DROP (13 rules), XRAY_KS_HOME first
jump, guard chain RETURN/DROP; filter OUTPUT ACCEPT (7 rules), no direct
XRAY guard jump. IPv4 mangle PREROUTING first two rules jump XRAY_WIFI,
11 rules in XRAY_WIFI, previously verified TCP/UDP TPROXY. IPv6 filter
FORWARD DROP (12 rules), OUTPUT ACCEPT (3 rules), no XRAY guard chain;
no default IPv6 route in the preceding all-tables snapshot. These are
structural observations, not end-to-end outage or no-leak proofs.
S98 calls rules script in a loop with sleep 60. Rule script SHA256
 ead5de5555aaab1170a140ca3d41ea546330a99ba873b1961bee536bc12780ef.
During 65-second passive ip monitor route observation, four IPv4 route
snapshot changes (one added, one removed, repeated), none in table 100,
none with expires fields; other three snapshot categories unchanged.
38 route event lines, 19 Deleted, zero table 100/local default lines.
Monitor was terminated by its owner after observation (rc -15).
Thus background IPv4 routing churn is independently observed without
candidate activity. Original mismatch cause cannot be attributed exactly;
no evidence implicates table 100 in observed churn. Do not waive strict
route witnesses, or claim the legacy S98 is safe. No raw route addresses
or secrets disclosed.

## Release gate
Previous unit CI 46023450359 SUCCESS 197/197 and packet reference CI
46023248399 SUCCESS remain applicable; not rerun. Actual production
TCP/UDP/DNS fail-closed under outage and IPv6 behavior remain unproven.
Disposable crash journal tests are not integration with current cron.
Physical installation/rollback still require separately authorized
transaction and journal-aware gating; no production deployment.
