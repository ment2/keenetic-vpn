# RC45: controlled Xray v30 migration with owner-approved downtime

Date: 2026-11-10. Repository `ment2/keenetic-vpn`, branch `feature/xray-v30-stable-tcp-ingress-lab-20261031`.

## Verified read-only result
Existing Keenetic job `abdc7c84-90f9-4d17-943b-cd0fdb0e76c3` completed `done`, exit code 0, without resubmission.

- `S97xray`: stop invokes `killall xray`, waits up to 10 seconds for SOCKS5 `127.0.0.1:10808` to disappear; start launches `/opt/sbin/xray run -config /opt/etc/xray/config.json`. Avoid S97 restart if any unrelated Xray is running.
- `xray-ks-home.sh`: maintains filter chain `XRAY_KS_HOME`, RETURN for `192.168.0.0/16`, DROP for `br0` source `192.168.1.0/24`, and ensures first FORWARD rule jumps to `XRAY_KS_HOME`. Watcher calls it every 15 seconds. This proves only Home forwarding protection, not full router OUTPUT, IPv6, DNS or UDP no-leak.
- `xray-safe-hourly.sh`: stages candidate in `/opt/etc/xray/config.pending.json` and exits, logging `STAGED_ONLY`; no apply or restart in inspected script. Cron runs it every 15 minutes under flock, so file races still need guarding.
- `S98xray-wifi`: 60-second watcher invokes `xray-wifi-rules.sh` on missing jumps/TPROXY/table-100 route. That script flushes and rebuilds XRAY_WIFI, and may leave partial rules if TPROXY fails.
- `xray-watchdog.sh`: checks SOCKS5 every 30 seconds and invokes S97 restart on failure.
- Kernel `4.9-ndm-5`, target TPROXY not registered; XRAY_WIFI contains nine RETURN exclusions, no TCP/UDP TPROXY. Module files exist with matching vermagic, but runtime loading unverified.
- Same-USB backup SHA and isolated extraction verified, independent off-USB recovery deferred. Owner authorizes planned outage and loss of active sessions, **not** physical commands.

## Revised controlled-outage strategy (not executed)
1. Preflight read-only: capture fresh boot ID, PID/start_ticks, all descendants and respawners, chain/route hashes, SOCKS and TPROXY listeners, kill-switch coverage, backup SHA, recovery shell access. Abort on drift.
2. Obtain separate approval for exact maintenance commands. Establish exclusive time-bounded fencing of S98, watchdog/S97 and competing cron writers; preserve independent kill-switch. Stop old Xray with accepted session loss. Never use blanket killall with unrelated instances.
3. With separate approval, activate kernel TPROXY module and verify target registration. If it fails, make no firewall change and restore services.
4. With separate approval, insert exactly two scoped TCP/UDP TPROXY rules after nine RETURN exclusions without global flush; verify actual packet path, TCP/UDP/DNS/IPv6 no-leak and fail-closed.
5. After physical acceptance, perform separately approved API migration with downtime. Verify SOCKS5, TCP/UDP and OpenAI reachability; re-enable supervisors only when they cannot destructively rebuild unexpected rules.
6. Rollback only transaction-owned rules and approved config/service changes; compare restored chain/route/kill-switch against preflight; no blind tar extraction. Recheck no-leak and remote access.

## Outstanding gates
S98 and watchdog fencing unproven; physical module activation and TPROXY packet path untested; router OUTPUT/IPv6/DNS/UDP no-leak unverified; same-USB failure risk accepted; live rollback rehearsal missing.

**HARD NO-GO for physical writes.** Scheduled downtime permission changes design constraints only.