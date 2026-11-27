# Dynamic VPN monitoring RC2 — 2026-11-27

## Status

Candidate developed, CI passed, real Keenetic probe acceptance passed for the
current ten-node subscription. No production Xray/updater/firewall/routing/
kill-switch change, no old monitor schedule change and no dashboard cutover.
HA supported state/dashboard access remains blocked (HTTP 401; no Supervisor
token exposed to the add-on agent). Do not obtain tokens from private files or
change authorization without the owner.

## Changes over RC1

- Separate owned-loopback probes: Google HTTP 204, unauthenticated OpenAI
  HTTP 401, independent public egress IP and geolocation. VPN is confirmed if
  any independent owned-route probe succeeds, not declared broken merely
  because a geolocation provider fails. No positive evidence means
  not_confirmed/missing; it does not identify a transport failure's cause.
- Display subscription endpoint host and port, external exit IP (with time
  and source), country code and city if available, independently timestamped
  results. Domain names are shown as supplied; no claim of resolved peer IP.
  Geo is approximate. If two IP witnesses disagree, do not attach geography
  to the other IP. Last known geography is explicitly historical, expires
  after 24 hours, and is invalidated on a new exit IP or configuration change.
- Unfiltered subscription refreshed on the 15-minute probe schedule. Stable
  node identity plus local-only full outbound generation witness prevents
  old evidence being attributed to reused tags or changed credentials/config.
  Active/pending membership by stable ID is refreshed by the 60-second
  publication cycle; configuration divergence is separately shown.
- Aggregate topic dynamic_rc2, distinct discovery identity, bounded 32 KiB
  only for this topic; legacy payload limits unchanged. Local LAN MQTT only.
  Current inventory refresh time and actual complete-probe coverage shown.
  Per-node history topics are non-retained state, retained discovery only,
  with remaining-freshness checks. History publication has a 120-second
  between-call budget; failure/partial publication must be visible in logs.
- Mobile Jinja card and six dynamic graph filters. No fixed seven-node list.
  HA timezone observed as Europe/Moscow. Offline Jinja is not live rendering.
- Probe schedule 03/18/33/48, membership every minute. 600-second probe
  budget; a node is not started with less than 55 seconds remaining. Future
  subscription growth or slow endpoints may result in incomplete coverage;
  do not claim a hard 15-minute SLA until repeated physical cycles pass.

## Verified CI

Run 46015411857, commit 21f7c795c0d9c7760ac7011e340dc8baa8586b14,
job 140561181891: SUCCESS, 162/162 tests. Includes exact status code tests,
owner loss, stable identity, credential generation, stale geo, changed IP,
payload capacity, subscription coverage, history TTL and mobile rendering.

## Physical evidence

- Staged seven probe/dependency files in a private monitor-only directory;
  exact Git blob verification and compilation passed.
- Single node: four successful owned-route observations; exit IP, country
  and city available, both exit-IP witnesses agreed. 9.16 seconds.
- Fresh full subscription fetch 1.04 seconds. Ten of ten nodes checked in
  82.59 seconds total. Six nodes returned HTTP 204; five returned HTTP 401;
  six provided exit IP, country and city. Four lacked positive observations;
  one confirmed VPN/Internet/geo but returned an unexpected OpenAI HTTP
  status. No actual addresses, credentials or identity digests in this report.
- Main Xray PID/start-ticks and config bytes identical before and after each
  physical test; no residual temporary Xray observed. Not a complete kernel
  no-leak proof or authenticated OpenAI test.
- Old monitor backup: init script, crontab, monitoring code archive; all
  SHA256SUMS verification passed. Stored privately on router.
- HA dashboard and dashboard registry backup verified via SHA256SUMS.
  No direct .storage edit was performed.
- HA state API returned 401; add-on SUPERVISOR_TOKEN absent. No live HA
  state/expiry or dashboard rendering acceptance yet.

## Deployment and rollback gates

Follow RC1 runbook for baseline, backup, exact old process ownership,
compare-and-swap on monitor-only schedule and preservation of the traffic
collector. Use reviewed RC2 source commit above and private local source
pins; do not copy credentials or raw subscription into GitHub.

New monitor-only schedule after acceptance:
```cron
3,18,33,48 * * * * cd RC_DIR && /opt/bin/python3 -B -m monitoring.rc2_cycle probe
* * * * * cd RC_DIR && /opt/bin/python3 -B -m monitoring.rc2_cycle publish
```
Replace RC_DIR only with verified persistent directory. Use bounded private
logs. Verify actual MQTT discovery fields, broker PUBACK, current entity ID,
state and expiry. Add a separate candidate HA view via supported editor or
authorized API. Run at least two scheduled cycles and verify coverage, timing,
resource load, removed nodes, new generation, local time and iPhone rendering.
Do not start old and new probe fleets concurrently.

Rollback: remove only new monitor cron lines using a checked diff, confirm
owned temporary child is gone; restore original monitor-only lines/init
from verified backup, restart only original VLESS collector if needed.
Restore old dashboard via supported UI/API; retain historical data and traffic
collector. Do not restart production Xray, change firewall/routes/kill-switch
or edit unrelated cron. No rollback has been needed for the isolated tests.

Production monitoring cutover remains NO-GO until authenticated HA acceptance,
MQTT state/expiry and repeat-cycle gates pass.
