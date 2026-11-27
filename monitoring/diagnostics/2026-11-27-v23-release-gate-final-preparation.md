# Geo-independent v23 — release-gate preparation, 27 November 2026

**Release status: HARD NO-GO for production.** This is a tested disposable
implementation and deployment design, not an installed native release gate.
No Keenetic production action or new Keenetic job was performed in this phase.
The previously accepted builder is unchanged.

## Baseline
- Live coherent generation: job de6c907e-805c-45c5-84ab-268c5e7c0de1, 10/10,
  92.7 s, real Xray -test PASS, four qualified. Report commit
  19765d4e79a3c029d72bb5496c4ab3e66d733364. No repeat live trial.
- Staged builder SHA256
  9e22a9b68a2e0fd5b1e66499778662419bc56cd8af491f229401269be2456ecd.
- Old builder SHA256
  00f08d13bd653ce72a57b0f73ec046f004dca1f900a36cfcec4d254dfa2392cf.
- Actual safe-hourly wrapper SHA256
  c63c0f171cda5b5f3150731e0706784b66977b256d737856edfcce15fba223c8.
- Old source pin values and new builder hash are explicitly recorded in
  release_gate.py. Only the builder pin may change. The three parser/probe
  dependencies and wrapper must remain byte-identical.
- Prior IPv4 reference packet CI 46023248399 SUCCESS, 8/8 positive and 0/8
  negative application receipts. Prior route churn evidence retained.

## New source and evidence
xray/candidates/geo-independent-v23/release_gate.py is deliberately restricted
to disposable roots with an explicit fixture marker. Do not copy it over
production or bypass that restriction. It exercises the proposed journal,
lock and invocation contracts with relocated paths.

Final source/test commit 6d1675ed1f20070ac37e94f5adf8a53ef0493f69.
CI 46025964177 SUCCESS 219/219, 22 new tests relative to 197. Earlier CI
46025820803 SUCCESS 217/217. Actual sanitized wrapper control flow is executed
in disposable paths with synthetic VLESS data, fake Xray/S97/curl; two new
integration tests verify successful wrapper invocation and failure/rollback.
No fake service result is described as a physical Xray restart.

### Transaction and cron
All cooperating operations hold the same existing lock inode for the entire
operation; external flock contention exercised. The gate never unlinks or
recreates the lock. File owner/type/link count/mode, dependency and wrapper
digests, pin schema/duplicate keys, exact old/new hashes and backup bytes,
lock inode and CAS before replacement are checked.
Private exact backups and journal are persisted with fsync. Journal phases:
prepared -> pins rename -> updater rename -> committed. Old pin JSON bytes
and both old modes are preserved. Each rename is atomic, the pair is not a
single filesystem transaction. A prepared or rollback journal is restored
before a cooperating cron launch; a committed pair must match. Unknown
generation, bad backup, mode mismatch or malformed journal blocks rather
than guessing. Real SIGKILL tests cover each meaningful phase and recovery.

Before executing the wrapper, create a durable running receipt. The lock
descriptor is not passed to wrapper descendants (avoid inherited long-lived
Xray lock). If the gate dies, the receipt remains. A real test kills the
gate parent while its synthetic child is still alive: next cron/recover
cannot execute or overwrite the pair. Receipt is removed only after a
successful child return and revalidation of the pair and dependencies.
Any nonzero return is conservatively fenced, including ordinary generation
failure or even a wrapper that successfully rolled back but returned 1.
No automatic receipt removal, no automatic PID signal, no claim of
uncooperative root fencing. Release needs a documented inspection/clear
procedure using boot ID, PID/start ticks, descendants, config/lastgood,
health and owner authorization. Power-loss on physical USB not proven.

### RC2 compatibility
The proposed monitor_probe method holds the same exclusive lock through
refresh/probe, passes only the verified four-pin dictionary, never restores
transaction files, rejects prepared/unknown generations and records its
own running receipt. Tests cover contention with cron and rollback,
prepared-state refusal and unknown monitor completion. Existing RC2
dynamic_monitor_cycle only observes the updater lock briefly; it is not
already integrated with this gate. A native adapter must invoke the audited
refresh/probe functions under the gate, rather than call the old cycle
which would try its own idle check. Publish-only work can retain its
monitor lock and must not imply fresh probe results. Existing old VLESS
and OpenAI collectors are independent and require separately approved
coordination. Do not claim RC2 schedule is already deployed.

## Independent packet gates
Previous IPv4 CI 46023248399 retained, not repeated. New IPv6 reference
CI 46025820668 SUCCESS at commit 07ecf07d5c3e4855cf0e6b2ef1cb20a4381a3e93.
Three isolated Linux namespaces; veth links only; synthetic ULA addresses.
TCP, UDP, DNS UDP and DNS TCP from client FORWARD and router OUTPUT.
Eight positive application AND independent AF_PACKET wire receipts.
Zero of eight negative application OR wire receipts. Each of eight
protocol/chain-specific ip6tables DROP counters incremented. First run
46025617659 failed at the positive TCP control; corrected lab IPv6 setup,
neighbor/route positive controls and timeout, not production settings.
No claim of a physical Keenetic IPv6 or TPROXY death path. No default
IPv6 route observed earlier is not proof of IPv6 no-leak. Router OUTPUT
policy ACCEPT and no IPv6 XRAY guard require physical acceptance.

## Native transition design (not executed; separate authorization required)
1. Reconcile exact native /opt mount and persistence, directory ownership,
   no unsafe symlink/parent replacement, supported fsync/rename, kernel,
   Python, boot ID, lock path/inode and old cron source. Determine how lock
   is recreated after reboot without a race. Check legacy S97/S98/watchdog,
   manual wrapper and old monitor actors; no uncooperative writer may
   bypass the gate. Retain independent recovery path. The current legacy
   cron uses external flock -n -o. Native gate must take that same lock
   itself; do not nest it beneath the existing external flock.
2. Build/review a native adapter from the fixture implementation, preserving
   all checks and using fixed audited paths. Establish persistent private
   journal directory and durable receipt semantics on actual USB. Validate
   path/mode/ownership and exact source hashes read-only before enabling.
   Make gate-aware cron the sole scheduled updater while the OLD pair is
   still installed; recheck exact cron bytes and all unrelated lines.
   Verify no old invocation or descendant and observe a normal old-pair
   cycle. An old cron/manual wrapper bypasses the journal; do not install
   the new pair until this bootstrap is accepted. No blanket crontab edits.
3. Separately coordinate legacy health/OpenAI collectors and staged RC2
   under the same lock with audited adapter. No new source or pin reads
   across a transaction; retain monitor-specific lock and private logs.
   Do not change unrelated traffic collector or production firewall.
4. Under the established lock, fresh CAS and quiet window, protected backup
   of updater, exact pin bytes/modes, wrapper, cron, active/pending/lastgood
   metadata and config backups. Keep private config locally, never upload.
   Install new builder and one changed pin via prepared journal and two
   same-directory atomic renames; readback and committed journal. No manual
   Xray restart for source replacement. On ordinary failure recover only
   recognized old/new objects; unknown state remains fenced.
5. Controlled actual IPv4/IPv6 no-leak acceptance with independent positive
   and negative TCP/UDP/DNS witnesses from client and router OUTPUT,
   including actual TPROXY process failure and recovery, DNS paths, IPv6
   policy routes and kill-switch. Requires separate authorization and
   recovery path; never disable the kill-switch or inject direct production
   traffic merely to prove a negative. Reference lab is not this gate.
6. Only after separately approved native acceptance may wrapper autoapply
   a new pool; check real Xray -test, health, S97/S98 identities, firewall,
   route structure and two scheduled cycles. Existing wrapper restarts Xray
   on pool change; no seamless cutover claim.
7. Rollback: stop further cooperating generations using lock/receipt,
   inspect any ambiguous child or boot state first. Restore exact old
   updater and pin bytes/modes using durable rollback phase; recheck
   dependencies and source pins. If pool was already applied, source
   rollback alone DOES NOT restore running Xray; use separately reviewed
   existing lastgood recovery with validated config and actual health.
   Verify DNS, HTTP204/401, kill-switch and controlled traffic. Restore old
   cron only after old pair, old runtime state and no outstanding journal/
   receipt/descendant are confirmed. Keep verified backups and recovery
   evidence; do not remove locks or blindly clear journal.

## Remaining blockers
Fixture-only gate, native adapter and bootstrap not yet executed or accepted.
Native boot/USB crash durability, manual/legacy actor fencing, receipt
reconciliation, actual physical IPv4/IPv6 no-leak under outage and live
install/rollback need separate maintenance acceptance. Exact old route
mismatch cause remains historically unproven; passive background churn was
observed. Full candidate probe and real Xray -test are already accepted,
not a reason to waive safety gates. No production authorization assumed.
