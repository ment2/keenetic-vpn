# Geo-independent v23 updater candidate — 2026-11-27

Status: offline candidate only; production deployment HARD NO-GO pending
separate physical acceptance and authorization.

## Confirmed diagnosis

The previous read-only investigation found vpn04 in the full subscription
and previous active configuration with matching stable identity. It was
absent from the active configuration at 17:46:09 Moscow time. The live
updater's last logged result was UNVERIFIED, with neither country nor IP.
Source gate was status != ok OR missing IP OR missing country; OpenAI
was not tested on that branch. RC2 had independently observed positive
HTTP 204 and HTTP 401 for vpn04 with geolocation timeout. This identifies
the exclusion mechanism, not the exact root cause of the failed geo
request at the later updater instant.

Live builder SHA256:
00f08d13bd653ce72a57b0f73ec046f004dca1f900a36cfcec4d254dfa2392cf
Git blob e9a5b68e9868f243847f950a350d82c9fc9d3d4c exactly matches
xray/production/opt/bin/xray-update-v23.py. Live safe-hourly wrapper
SHA256 c63c0f171cda5b5f3150731e0706784b66977b256d737856edfcce15fba223c8;
its blob 93a2963988436241b314e6cda74e0337fbb56abe differs from the older
GitHub wrapper in the monitoring branch. Read-only inspection confirmed
the live builder path, --output, pending, lastgood, validation and
rollback markers. The wrapper was not edited or exercised.

## Candidate changes

Path: xray/candidates/geo-independent-v23/xray-update-v23.py
Git blob: 54287f3a483e045a16a3bb7296c27d5ed3a7a5bc.
Based on exact live builder. Existing subscription reader, local parser
interface, candidate shape, inbounds, balancer, fallback, observatory,
blackhole catch-all and Xray -test validation preserved.

Four separate HTTPS requests run through a single temporary VLESS Xray
per node, with explicit loopback SOCKS, blackhole default, no direct
fallback, no curl config, no redirects and normal TLS verification.
The listener inode must belong to the child before/after each request.
Admission requires BOTH HTTP 204 and HTTP 401, each with a verified
owned route, exact integer code and current per-node timestamp. HTTP
401 is unauthenticated reachability, not an authenticated OpenAI test.
Exit IP and geo are diagnostics only; neither their absence nor a
normal service error gates admission. No optional probe can substitute
for either mandatory check. Status-only logs avoid raw exit addresses
or credentials; downstream log consumers must be checked before release.

No stale monitoring cache reused. Probes run serially; unknown child
cleanup aborts the generation, not merely one node. Explicit outbound
chaining and ambiguous VPN selector tags are rejected. Cycle budget
720 seconds, conservative 55-second per-node allowance and 40-second
validation reserve; budget exhaustion aborts the generation rather
than exporting a partial traversal. Per-node timestamp age checked
when deciding admission; this is not a hard final-pool freshness SLA
or a kernel no-leak proof. Real timing and child termination on device
must be accepted separately. Output remains --output, new private file
only (exclusive create, mode 0600, fsync); empty pool or failed Xray
validation yields nonzero exit without candidate export. Existing active
pool remains unchanged on candidate-generation failure, under existing
wrapper behavior; this is not a claim that every previous active node
has been freshly requalified.

## Tests

Final code/test commit 532b4fa6c63b16729832fab69bb7c6db182db533.
CI 46021137812, job 140580819500, SUCCESS, 182/182 tests,
16 new updater regression tests relative to previous 166.
Test file monitoring/tests/test_geo_independent_v23.py.
Includes vpn04 geo timeout + both mandatory successes admitted; missing
IP/geo; exact HTTP response codes; owner loss; stale/future/malformed
evidence; independent probe ordering even when internet fails; real
Linux loopback listener inode; explicit SOCKS proxy; cleanup failure;
budget exhaustion; no direct outbound; fallback membership; Xray test
failure and empty pool; output collision/symlink; selector ambiguity;
no raw data in logs. Candidate edits trigger isolated CI. Xray binary
validation and HTTPS responses are mocked in this offline suite; no
live Xray probe or deployment was performed for this candidate.

## Separate acceptance / rollback plan (not executed)

1. Reconcile exact live autoapply wrapper source and its lock, failure,
   pending, lastgood, rollback and log-parser behavior in disposable
   tests. Verify nonzero/empty/invalid generation cannot apply. Verify
   no leakage, including owner/child cleanup on failure/timeout. Do not
   substitute the older staged-only GitHub wrapper.
2. With separate approval, stage only candidate in a private persistent
   directory. Verify exact reviewed Git blob and root-only file mode,
   compile/import, parser compatibility, and live wrapper interface
   without replacing active builder. Run in an isolated quiet window
   under approved coordination, no concurrent updater/probe fleets.
   Use a private new output file, not active/pending config; compare
   eligible stable IDs, timings, mandatory results, and optional geo.
   Verify main Xray PID/start ticks, active config digest, firewall,
   routing and kill-switch witnesses unchanged before/after.
3. Before any authorized install, create protected verified backups of
   old updater, monitor source-pin file, existing config/pending/lastgood
   and wrapper/cron metadata. Record exact pre-change digests and modes.
   Acquire existing updater lock in accordance with actual wrapper.
   Atomic replacement of updater only, preserve permissions. RC2 full
   subscription adapter pins updater SHA256; update ONLY that pin to
   the separately accepted new SHA as a coordinated change, preserving
   other three pins. If pin update fails, restore old updater and pin;
   do not bypass verification. No manual restart of Xray.
4. Use existing validated wrapper to apply only after separate live
   authorization. Verify normal scheduled cycles, active/pending
   identities, OpenAI/HTTP204, actual no-leak/kill-switch, and rollback
   witnesses. If failed, stop further new generations using existing
   coordination and restore exact previous updater/pin with CAS and
   verified backups; if pool changed, use existing lastgood rollback,
   not an ad hoc config/firewall edit. Verify Xray, DNS, HTTP, kill-switch
   and monitor health after rollback. Never auto-refresh pins blindly.

No change to live updater, Xray, wrapper, firewall, routing, cron,
monitoring schedules, kill-switch or production configurations. No
credentials, subscription URLs, real endpoint addresses or raw config
are included in this public report. Physical acceptance and production
rollback are not yet demonstrated.
