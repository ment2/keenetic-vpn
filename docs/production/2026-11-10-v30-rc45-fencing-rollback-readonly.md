# RC45: read-only evidence for S98 / watchdog / kill-switch and fencing plan

Date: 2026-11-10. Repository `ment2/keenetic-vpn`, branch `feature/xray-v30-stable-tcp-ingress-lab-20261031`.

## Verified job
Existing Keenetic Mobile task `40b90288-041d-44fd-b7ee-976ddb0f4e27` returned `done`, `exit_code=0`, without resubmission. Read-only grep output:

- `/opt/bin/xray-wifi-rules.sh`: line 3 assigns `/opt/sbin/iptables`; line 7 comments on TPROXY routing; line 36 contains `-j TPROXY --on-port 12345`.
- `/opt/etc/init.d/S98xray-wifi`: line 5 assigns `/opt/sbin/iptables`; line 9 tests a PID file and live PID; line 12 begins `while true`; line 20 checks `iptables -t mangle -L XRAY_WIFI -n` for TPROXY; line 26 sleeps 60 seconds; line 33 invokes `kill` on a PID from its PID file; line 36 has a `restart` branch.
- `/opt/bin/xray-watchdog`: `UNREADABLE` at the inspected path. This does NOT establish that the running watchdog has no accessible backing script elsewhere.
- `/opt/bin/xray-ks-home-watch.sh`: `while true` at line 4 and `sleep 15` at line 7.

These are grep-selected fragments, not complete control flow. In particular, S98 might invoke the rules script conditionally; do not assert its exact action without reviewing the relevant context.

## Proposed safe fencing and rollback plan (NOT AUTHORIZED TO EXECUTE)
1. Before maintenance, capture fresh boot ID, chain rules and counters, module registration, all S97/S98/S99/watchdog/cron parent-child identities, PID start_ticks, service status and kill-switch behavior. Confirm the current nine RETURN exclusions and zero TPROXY rules; abort if drift.
2. Review complete S98 and rules-script control flow, watchdog actual executable/command line, PID-file semantics, cron re-spawn paths and process descendants. Determine which actors can rewrite XRAY_WIFI, reload Xray, or relax fail-closed. Do not guess from PID alone.
3. Prepare a separately approved maintenance transaction with a single owner, atomic generation/boot/PID identity guards, preverified off-path rollback instructions, and time-bounded watchdog. Prevent competing privileged writers from changing the target chain only for the controlled window; preserve independent kill-switch protection. No blanket `killall`, no disabling the kill switch, no global flush of mangle/filter chains.
4. Verify `xt_TPROXY` registration with a separately approved module activation only after safety gates. The presence of matching ELF vermagic and empty `depends=` does not establish runtime support. Abort without firewall writes on any failure.
5. If approved later, insert exactly two scoped TCP/UDP TPROXY rules only after the nine RETURN exclusions, with exact-match rollback deletion, no-leak tests and service interruption acknowledged. Validate TCP and UDP probes, fail-closed on tunnel loss, and absence of competing writers. Abort and roll back on unexpected result.
6. Rollback must remove only rules introduced by the transaction, restore prior module/service state only when safe, verify original chain snapshot and independent kill switch, and release fenced writers under controlled checks. Never extract the full tar over `/opt` automatically.

## Outstanding blockers
- Physical `TPROXY` target not registered, module not loaded at last check; activation untested.
- S98 is a periodic watcher; complete conditional behavior, descendants and restart policy not yet established.
- Watchdog path unreadable and kill-switch watcher control flow not fully inspected.
- Backup integrity and isolated extraction verified, but backup is on the same USB; off-USB recovery deferred by owner.
- No production change, module load, iptables change, restart, cron change or cutover approved.

**Decision: HARD NO-GO for physical TPROXY and API cutover.**
