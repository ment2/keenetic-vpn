# RC2 live Home Assistant acceptance — 2026-11-27

## Authorization
The earlier HTTP 401 was due to a stripped SSH agent environment. The
documented Home Assistant add-on S6 launcher `/command/with-contenv` made the
existing Supervisor-provided credential available to the process. The
authenticated Core REST proxy returned 200; authenticated WebSocket
Lovelace read/write worked. No credential was printed, copied, persisted,
rotated, or extracted from private files; no permissions changed.
Reference: https://developers.home-assistant.io/docs/apps/communication/

## Live MQTT
- Fresh full subscription: ten actual nodes. Private local snapshot created
  via the pinned existing reader/parser, without running updater main.
- Inventory-only shadow aggregate: 4513 bytes, schema 2, ten nodes,
  probe_complete=0, non-retained state, PUBACK. HA REST state ok.
- HA Recorder independently recorded transition ok -> unavailable
  after 150.000 seconds, then restored ok following a new publication.
  Live HA template showed the unavailable notice and no stale green data.
- Controlled shadow full cycle: ten of ten complete, 91.44 s,
  Internet HTTP 204 6, OpenAI HTTP 401 5, geo 5, VPN witness 6.
  Main Xray PID/start-ticks/config digest unchanged and no other
  Xray process at before/after checkpoints. This is not a full kernel
  no-leak proof. Real aggregate 5070 bytes, PUBACK, Recorder confirms
  schema=2, count=10, probe_complete=10.
- Canonical HA markdown template rendered all 10 tags without error
  through live Core template API, no synthetic state injection.
- Existing history publisher first created 60 enabled MQTT entities,
  but all lacked live attributes/state. Separate retained discovery phase,
  five-second settle, then non-retained state phase recovered all six
  graph filters (10 matching entities each). This is consistent with
  asynchronous discovery/subscription delivery, not a broker PUBACK failure.
- Canonical rc2_history.py now uses two phases, five-second settle,
  120-second between-call budget and conservative 180-second expiry guard.
  No retained state. Regression CI 46018315554, commit
  c41a8b510c32978e87b3779f5053581e6794c886: 165/165 SUCCESS.
  Staging file write verified by agent, backup created. Exact staged Git
  blob 9d0a5d61f138603255bba8b3e641a7c2a7a84f90 matched; patched
  publisher completed 10/10 nodes in 6.37 s, aggregate PUBACK 10/10.
  Final live HA template readback: 10/10 tags, no errors, all six
  graph filters 10/10, state ok, probe_complete=10.

## Dashboard and monitor-only staging
- Supported Lovelace WebSocket API: existing vpn-monitor dashboard read,
  exact local private backup created, re-read equality check before save.
  Added rc2-shadow view with seven cards; original view unchanged,
  saved config readback equals requested config. No direct .storage edit.
- The six graph filters returned ten matches each in live HA template
  API after two-phase publication. Physical iPhone/browser visual rendering
  has not been independently observed.
- Four source digests written to protected monitor-only pin file;
  mode 0600 verified. Existing updater source files unchanged.
- Old health/OpenAI schedules and traffic collector still in place.
  No production Xray/updater/firewall/routing/kill-switch or cron changes.
  The two scheduled cycles and physical rollback rehearsal remain open.

## Next gate
Keep
original dashboard view as rollback. Use the existing authenticated browser
or confirm visual rendering of the shadow view; then perform only the
monitor-only cutover in a quiet updater window, with refreshed verified
backup/CAS, exact old process identity and bounded logs. Verify two
scheduled cycles and rollback plan; do not start parallel probe fleets.
