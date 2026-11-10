# Xray v30 RC45: recovery readiness and read-only gate plan

Date: 2026-11-10. Branch: feature/xray-v30-stable-tcp-ingress-lab-20261031.

## Confirmed baseline
- On-USB archive: `/opt/backups/xray-v30-prechange-20261110-161607/xray-production.tar.gz`, 9.9 MB, 104 tar entries (33 etc/xray, 20 etc/init.d, 50 bin/xray, 1 sbin/xray).
- SHA256 and gzip checks passed. Isolated extraction to `/opt/backups/xray-v30-prechange-20261110-161607/restore-test` succeeded (exit 0). Restored `etc/xray/config.json` was nonempty; restored `sbin/xray` executable.
- Follow-up read-only job `b58e34b5-e7bd-4ebc-8055-4b75848ff6c3` was **running** on latest polls. It compares extracted regular files against archive bytes and checks permissions/disk. **No bytewise equality or permissions success claimed yet. Do not resubmit.**

## Next read-only gates
1. Poll only existing job; capture final exit code and exact result. On `MISMATCH`/`MISSING`, do not automatically rewrite any file.
2. Inspect archive coverage and symlinks without exposing credentials; archive consistency does not prove live production equivalence.
3. Recheck boot ID, vendor module target registration, chain, Xray PID/start_ticks, and competing S97/S98/S99/watchdog/cron descendant identities immediately before any physical change.
4. Draft a narrow rollback preserving independent fail-closed, without extracting tar wholesale over live `/opt`.
5. Require separately approved exact command for any future router write, module activation, iptables modification, supervisor quiesce or restart.

## Physical NO-GO
`xt_TPROXY.ko` exists but target registration/activation was not proven. RC45 observed nine XRAY_WIFI RETURN exclusions and zero TPROXY. Same-USB archive is not independent disaster recovery; owner deferred HA backup. Controlled VPN interruption may be acceptable for first API migration, but fail-closed and rollback must be proven.

**HOLD / NO-GO for physical TPROXY changes and cutover.**

Archive/config may contain VPN secrets. Do not upload archive, credentials, or unredacted configs to GitHub/Library.