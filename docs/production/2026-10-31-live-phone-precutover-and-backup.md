# Xray v30: live phone traffic, API candidate preflight, private rollback backup

Date: 2026-10-31 (UTC measurements approximately 10:39–10:47). Only repository `ment2/keenetic-vpn`, branch `feature/xray-v30-stable-tcp-ingress-lab-20261031`.

**Scope:** bounded pre-cutover verification on actual Keenetic Ultra and creation of a root-only private backup. **No live cutover, Xray stop/restart, production config replacement, firewall/route/cron/watchdog changes, or Git merge/deploy.** User now has a phone connected and authorized interruption if technically safe; this is not evidence of a tested recovery path.

## Worker and live router actions (all one-shot, no duplicate jobs)

- Worker `get_permission_status`: `remote_enabled=true`, `owner_admin_enabled=true`, revision 2, scopes diagnostic/exec/read_file/write_file. Administration is authorized; do not confuse permission with production readiness.
- Diagnostic `d0d6a900-ffea-42e2-b037-4b5a3c3b7645`: **done, exit 0**, router ONLINE, load average `0.65/0.56/0.55`, approximately 3.53 GB free.
- Read-only full preflight `9a87b569-3ae8-40e0-97a6-d0ad4d953969`: **done, exit 0**. Kernel `4.9-ndm-5`; main Xray PID **13546**, start ticks **100216734**; TCP SOCKS `127.0.0.1:10808`, TCP+UDP `:::12345`, all owned by main Xray. `fwmark 0x40000000/0x40000000 -> table 100 -> local default dev lo`. Initial counters: TPROXY TCP 10492 pkts, UDP 1032 pkts. Home kill-switch DROP rule counted 956 pkts at baseline. No actual phone source attribution.
- Read-only live traffic and network test `6e97f817-c999-4d85-b64c-33ab37465777`: **done, exit 0**. TPROXY counters within five seconds increased TCP **17103 → 17208 (+105)**, UDP **1589 → 1590 (+1)**. `curl --socks5-hostname 127.0.0.1:10808 https://api.openai.com/v1/models` returned **HTTP 401 in 0.516569 s** as expected without auth. IPv6 FORWARD default DROP visible, but full IPv6/DNS leak audit **not proven**. Host DNS entries deliberately redacted.
- API candidate config validation `c1a9c563-1754-46b1-9b1d-7f91d70b63c5`: **done, exit 0**, constructed on router using existing active configuration, but only inside a private `mktemp` folder removed on exit; no secret contents transmitted. Original 2 inbounds, 8 outbounds, no `freedom/direct` outbound. Added `HandlerService/RoutingService` and `127.0.0.1:19090` `dokodemo-door` API plus loopback routing; `xray run -test` returned **Configuration OK**. Candidate SHA256 `b06eaa6f0c8ef33ba549325b05cf6c979db93ac3b190ad5ca628d67b0e8deb39`; candidate **was removed**, not staged persistently. Deprecation warnings for VLESS/gRPC/`headers.host` remain for future migration. Active config SHA unchanged.
- Read-only recovery capability check `b39e77f4-e471-4a18-93da-c8f8354f5b04`: **done, exit 0**. Dropbear listens on LAN ports **22** and **222**; local SSH access from the user's phone **not yet confirmed**. `flock`, `mktemp`, Python 3.13 and Xray available; `/opt/bin/timeout` and `/opt/bin/socat` absent. Xray config and pending config are mode 0600 in root-only directory; same USB filesystem approximately 3.5 GB free.

## Locally retained backup, no external secrets

- Backup task `471c1e06-5e16-4331-9f4a-21d2f654726e`: **done, exit 0**.
- Root-only directory: `/opt/var/backups/xray-v30-precutover-20261031-1045Z`.
- **11** source/binary/config files plus **5** network-policy snapshots. Files saved mode 0600; parent 0700. Original permissions and SHA256 kept in private `manifest.json`. Source and copied bytes verified equal.
- Manifest SHA256 `f27c336f66f1bbb9ef22a82f7e8aa84f80f9bee808b3a87abf6a5372e79d5c62`; original/backup/active Xray config SHA256 all `66d074f32fffbf4a251576c8297714e9647174546e9e73e5bf27cf2768efe6d7`.
- Local backup validation `6b057959-8c7e-49c4-bb6d-7c10ea100681`: **done, exit 0**, 11 backup entries re-hashed and checked with root-only modes; `xray run -test -config <backup>` returned **Configuration OK**; 5 backed-up shell scripts passed `sh -n`. **NOT** a complete live rollback test: no production restore attempted.
- During that verification `pidof xray` briefly listed main 13546 and PID **15329** (start ticks **110990977**). A follow-up read-only diagnosis `76146008-aa14-40fb-9067-0de1a536afed`: **done, exit 0**, found **only** production PID 13546 with original start ticks, owning SOCKS and TPROXY TCP/UDP. Transient process exited before identification; do not attribute its origin without evidence, do not invoke `killall xray`.

## Current decision and unblock criteria

**FIRST PRODUCTION CUTOVER = BLOCKED.** The old process has no API; legacy `S97xray` invokes broad `killall xray`, old watchdog is running, `S98xray-wifi` can rewrite `XRAY_WIFI` during a transition. The candidate was validated as a file, **not actually bound on production sockets**. One-time migration will necessarily risk dropping existing sessions and could isolate the remote agent.

Before initiating live cutover:
1. Confirm from the **connected phone** that direct local SSH login with Termius to `192.168.1.1:222` works even without mobile VPN. A listening local socket alone is not an independent tested recovery channel.
2. Produce, review and test an exact PID/start-ticks-scoped first-cutover script plus autonomous rollback guard, not `S97xray restart` and never `killall xray`; cover watchdog and `S98xray-wifi` races without disabling fail-closed protections.
3. Re-read live PID/start ticks and config/binary SHA immediately before executing. Preserve local backups and do not publish secrets.
4. Separate exact-operation approval in addition to general network interruption tolerance.
5. Establish live SOCKS, TPROXY TCP/UDP, IPv6/DNS leak, proxy-dependent service and kernel fail-closed post-switch checks. Unknown readiness => recover old snapshot or remain fail-closed.

No production Xray config, process, kernel route, firewall, cron, watchdog, or init script changed. Creating the root-only private backup was the **only persistent router filesystem change** during this stage.
