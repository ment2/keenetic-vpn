# Dynamic VPN monitoring RC1 — 2026-11-27

Status: staged candidate, not installed. No live Xray, firewall, routing,
kill-switch, production updater or production cron mutation was performed.
The repository is public; this report deliberately excludes subscription
URLs, VLESS UUIDs, endpoint addresses, node IDs, passwords and local job IDs.

## Findings

- Fresh subscription read through the existing reader: 10 VLESS entries.
  Existing parser returned ten valid outbounds; active configuration had four
  matching entries and no pending configuration at the inspection moment.
- Old dashboard statically listed seven tags, including old identities.
  The VPN02 and VPN05 labels were reused for different endpoint identities.
  MQTT registry contained duplicate OpenAI sensor suffixes for two nodes.
- Old VLESS and OpenAI collectors independently read the active configuration.
  Fresh local history included one node with failed generic HTTP and reachable
  OpenAI, while the dashboard did not display the corresponding VLESS result.
  HTTP results must remain independent. Missing/stale is not success.
- Target: Linux 4.9 little-endian, Python 3.13, readable proc TCP/FD tables,
  private monitor state directory. HA already has auto-entities resource.
  HA registry was inspected; live state API from the add-on returned failure.
  No authenticated HA template/render or broker acceptance is claimed.

## Candidate

- full_subscription_snapshot.py calls only the verified existing subscription
  reader and parser, never the updater main. Requires pinned digests, root
  ownership, protected source files and private output. Atomic local full
  snapshot; no partial inventory on parser failure.
- isolated_pair_probe.py creates one temporary private Xray per node with
  loopback SOCKS, explicit blackhole default and child listener inode witness
  before/after each request. Explicit curl proxy, no curlrc, no redirects.
  Generic egress and unauthenticated OpenAI HTTP 401 remain separate. This
  is not evidence of an authenticated API or a full kernel no-leak test.
- dynamic_snapshot.py joins stable identities, not labels, and publishes
  bounded, timestamped aggregate. Missing/stale/future-dated observations
  never count as green. Inventory expires after 30 minutes, published snapshot
  after 150 seconds; observations after 1800 seconds.
- dynamic_history.py retains discovery only, publishes fresh non-retained
  per-node measurements with stable IDs. Existing old history stays intact.
- dynamic_monitor_cycle.py separates 15-minute probe and 60-second publication
  schedules. Probes start at minutes 03/18/33/48 with a 480-second budget
  (incomplete observations shown missing); updater lock is only briefly
  observed, not held during network work. This is not a mutual-exclusion
  guarantee against a manually started updater.
- Dynamic mobile card and auto-entities history filters show only current
  inventory; labels can be reused without reassigning old observations.

## Preflight and staged application (not executed)

1. Record active Xray PID/start ticks, config SHA, current firewall and
   kill-switch status and current updater/monitor schedule; do not export raw
   configuration or secrets. Distinguish legitimate updater generations from
   changes caused by the monitor. Do not apply during recovery/rollback.
2. Create root-only timestamped backup directory on persistent local storage.
   Copy only the current monitoring init script, exact crontab, monitoring
   source directory, and relevant HA dashboard JSON/config; keep SHA256
   manifests. Preserve existing MQTT registry/history and traffic collector.
   Never upload live config, credentials or backup bytes to public GitHub.
3. Stage only monitoring sources in a new persistent RC directory (not /tmp),
   root-owned and non-writable by other users. Verify against reviewed commit,
   compile/import and run tests using synthetic data. Prepare root-only
   dynamic-source-pins.json containing the separately reviewed four local
   source SHA256s; do not auto-refresh pins after a code change.
4. Before adding any schedule, run one isolated node probe in a quiet window,
   verify listener ownership and child cleanup, inspect main Xray identity,
   CPU/memory, DNS and existing kill-switch without changing them. Then one
   full cycle, measure actual elapsed time and number of nodes. Stop on
   unexpected child/port ownership, budget overrun, broker error or any
   production impact. Do not start a parallel production probe fleet.
5. Establish new aggregate MQTT discovery and per-node history using the
   existing local credential file without displaying its content. Check
   PUBACK and actual HA entity ID, state, timestamps, attributes, and expiry.
   Verify the proposed discovery fields are accepted by the installed HA
   version. Render a separate candidate view; use supported HA dashboard
   editor/API, not live direct edits to cached .storage files.
6. Only after a successful shadow cycle and explicit cutover gate, stop the
   old VLESS health process using exact PID, cmdline and start ticks; disable
   only its start line in S99zz-vpn-monitoring and only the old OpenAI cron
   line. Leave the traffic collector and every Xray/updater/kill-switch
   service unchanged. Use compare-and-swap on crontab and init script, with
   atomic local replacement and verified backup. No killall, no service
   restart of Xray.
7. Proposed monitor-only cron entries, after replacing RC_DIR with the
   verified persistent path (do not install blindly):

   ```cron
   3,18,33,48 * * * * cd RC_DIR && /opt/bin/python3 -B -m monitoring.dynamic_monitor_cycle probe
   * * * * * cd RC_DIR && /opt/bin/python3 -B -m monitoring.dynamic_monitor_cycle publish
   ```

   Use private bounded log handling. Preserve unrelated cron entries.
   Verify all ten current entries (not necessarily healthy), membership
   refresh at 60 seconds, and at least two 15-minute cycles. Verify no
   stale positive result, removed nodes omitted from current views, new
   identities appear and graphs only use matching identities. Confirm
   local time and iPhone rendering. Replace old VPN view only on acceptance;
   leave traffic view and historical data intact.

## Rollback

- Disable exactly the two new monitor cron entries using a checked diff,
  wait for owned probe child to finish or explicitly clean up only that
  verified process. No Xray restart.
- Restore monitoring init script and original monitor schedule from verified
  backup with a compare-and-swap check; if unrelated cron edits occurred,
  restore only the matching old monitor line. Restart only old health
  collector if necessary, never the traffic collector or production Xray.
- Restore old dashboard through supported HA configuration editor/API;
  retain historical data. New state topics expire; do not mass-delete
  retained discovery or unrelated MQTT entities. Any targeted cleanup is
  a separate exact-topic operation.
- Keep private snapshot and backups on router; do not copy credentials
  or raw outbound settings into repository, diagnostics or public logs.

## Acceptance gate

Offline CI is not physical acceptance. Production application remains NO-GO
until actual isolated probe, resource/timing, MQTT discovery/expiry,
supported HA edit/render, backup and rollback checks are verified. No
production deployment or monitoring cutover was performed in this stage.
