# Geo-independent v23 — separate acceptance, 2026-11-27

Status: HARD NO-GO for production installation. No production change made.
Baseline candidate: commit cfd1c5c37b30445f2dcf7ed64559d165fef5ceb5;
candidate Git blob 54287f3a483e045a16a3bb7296c27d5ed3a7a5bc,
SHA256 9e22a9b68a2e0fd5b1e66499778662419bc56cd8af491f229401269be2456ecd.
Staged only as /opt/var/lib/vpn-monitor/geo-independent-v23-candidate.py;
write and subsequent exact Git blob/SHA256 verified. No live builder replacement.

## Exact installed wrapper
Live SHA256 c63c0f171cda5b5f3150731e0706784b66977b256d737856edfcce15fba223c8.
All 127 source lines reviewed; two URLs redacted in captured text.
External cron uses flock -n -o /opt/tmp/xray-update.lock, mode 0600.
Wrapper itself has no internal lock. It requires successful generation, nonempty
candidate, VLESS membership and Xray -test; identical config skips restart.
It stages pending, validates active rollback config, saves verified lastgood,
atomically renames candidate over config, restarts S97 and checks 204 then 401.
Failure/signal during APPLYING invokes rollback by atomic config rename, S97
restart and health check; rollback failure is CRITICAL. A restart is not seamless.
EXIT/HUP/INT/TERM traps do not establish crash/SIGKILL/power-loss recovery.
Pending may remain on failure; post-rollback health is not guaranteed.
All four current RC2 source pins match live sources. No pin changes.

## Offline CI
46022171563 SUCCESS 189/189: seven additional tests of captured wrapper
control flow, using relocated disposable paths, synthetic URLs and mocked
service/health commands; includes real external flock contention.
46022344259 SUCCESS 190/190, commit 7f2450806c1a2ea68d3231606556b5408c31e969:
additional real curl dead-SOCKS test with local destination and hostile
NO_PROXY environment. No direct connection accepted. CI is not live
S97/TProxy packet-path or physical rollback proof.

## Physical staging-only trial
First quiet-window trial with existing exclusive updater lock ran nine of
ten positions in one fresh subscription; 82.37 seconds. A conservative
MCP transport deadline guard aborted before vpn10. No candidate exported,
no real full-generation Xray -test completed.
vpn01, vpn06, vpn07, vpn09: ALLOWED, all four probes ok.
vpn02, vpn04, vpn05: all four network_error, UNVERIFIED.
vpn03: all four timeout, UNVERIFIED.
vpn08: internet/openai/exit IP timeout; geo network_error, UNVERIFIED.
Separate fresh read (ten positions), vpn10: internet ok, OpenAI http_error,
exit IP ok, geo timeout, UNVERIFIED, 10.58 seconds. No exact HTTP status
recorded in this observation. Tags tested 10/10 across TWO reads; not a
single coherent subscription generation. No identity equality between the
two fresh reads claimed. vpn04's present failure differs from the earlier
case with successful mandatory probes and geo timeout.
In both trials, main Xray PID/start ticks/child inventory, active/pending/
lastgood/config and builder/wrapper/pins file digests, normalized IPv4 and
IPv6 firewall rules and IPv4/IPv6 rules/routes matched before/after.

## Negative direct-fallback test
Actual staged code, actual curl and temporary Xray, synthetic loopback
destination and refused loopback endpoint. Dead SOCKS: no direct destination
connection. Dead VLESS: four owned SOCKS requests failed, no direct destination
connection, no qualification. Main/child, file and firewall witnesses matched.
Route witness did NOT match (exit 1). Before/after route hashes were compared
as an aggregate, individual diff was not retained. Subsequent read-only
four-second samples: v4 rules 6/6, v4 routes 90/90, v6 rules 2/2, v6 routes
66/66, exact equality in all four, no expires fields. This does not explain
the preceding mismatch. strace absent; tcpdump available but not used.
No proof of full WAN/TProxy/kill-switch no-leak. Do not waive this gate.

## Installation and rollback preparation — NOT executed
1. Resolve route witness mismatch with per-table private before/after
   snapshots, sanitized structural diff, exact process/child evidence;
   no rules/routes edits. Obtain a coherent full subscription run with a
   bounded acceptance harness that respects the 180-second MCP limit and
   reserves validation/cleanup time; verify real Xray -test and no export
   if incomplete. No detached job or bypass of transport deadline.
2. Establish independent controlled packet-path negative witness for
   TCP/UDP/DNS and kill-switch in a disposable lab or explicitly authorized
   acceptance; synthetic loopback fallback alone does not establish this.
3. Before any authorized install, acquire existing exclusive updater lock
   in quiet window; check inode, permissions, old builder SHA and all four
   pins, wrapper SHA, process identity, active/pending/lastgood generation,
   cron and rules. Ensure no concurrent manual/monitor probe. Use protected
   persistent backup directory, exact modes, byte hashes and fsync of files
   and parent directories. Back up builder and pins, config/lastgood/pending
   and metadata; never publish raw config or credentials.
4. Stage new updater and pin JSON in same respective target directories
   with restrictive permissions; preserve other three pins; verify candidate
   digest and Python compile/import (no main). Journal old/new hashes and
   transaction stage. Under the lock, recheck CAS before each rename.
   Replace pin first (monitor fails closed on temporary mismatch), then
   updater; each rename atomic, fsync directories, verify pair. Two paths
   cannot be atomically replaced as one filesystem operation. On ordinary
   failure, atomically restore both exact backups under lock, CAS-protect
   against unexpected writers; verify old hashes. Power-loss/SIGKILL needs
   a durable recovery/fencing design before strict transactional acceptance;
   the current cron does not inspect a journal. Do not claim crash-atomicity.
5. No Xray restart merely for installing the builder. Actual autoapply and
   rollback require separate live approval: preserve current wrapper and
   use its validated lastgood restore path; verify S97 health, HTTP204/401,
   DNS, routing, kill-switch and actual controlled traffic witnesses.
   If a pool was already applied, reverting the builder/pins alone does
   not roll back the running pool. Stop/fence further generations with
   approved coordination, restore pair and use verified lastgood recovery.
6. Confirm monitor reads new pin, full subscription and two scheduled cycles.
   Do not blindly refresh pins or overwrite an unexpected generation.

No live builder, wrapper, pin, config, cron, firewall, routing or kill-switch
changes performed. Only non-production staged candidate and temporary probes.
Remaining gates: coherent generation validation, unexplained route mismatch,
independent no-leak/kill-switch witness and separately approved installation.
