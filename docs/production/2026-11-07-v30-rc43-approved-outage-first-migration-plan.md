# RC43: controlled first production API-enabled Xray migration, outage allowed

2026-11-07. Repository ment2/keenetic-vpn; only feature/xray-v30-stable-tcp-ingress-lab-20261031. Status: staged production-adjacent preflight and execution checklist. No live router changes performed by RC43.

## Updated operator decision, replacing the wrong seamless prerequisite

The owner explicitly permits a service interruption for first migration. Existing TCP and UDP sessions may be broken by the one-time restart from API-less Xray 26.2.6 to API-enabled Xray. This applies to FIRST MIGRATION only. Future pool refresh can still aim for lossless handover, but old activeConn enumeration, atomic packet-preserving session transfer and the RC40-42 seamless conditions are not a prerequisite for one maintenance cutover.

The exact outage duration is not measured or guaranteed. A 15-second trial and 90-second guardian are configured test timings, NOT guaranteed outage or restoration deadlines. Preserve original fail-closed kill switch; never fall back to freedom/direct Internet.

## Already done: avoid duplicate deployment

- Previous live router preflight and private backup were completed Oct 31. Backup archive /opt/var/backups/xray-v30-precutover-20261031-1045Z, 11 original files plus five rule/routing snapshots; manifest SHA f27c336f66f1bbb9ef22a82f7e8aa84f80f9bee808b3a87abf6a5372e79d5c62. Archive bytes verified, but original modes differ for nine archived files and need restore-specific validation.
- Existing v30_first_cutover_canary.py installed once on router at /opt/bin/v30_first_cutover_canary.py, root-only 0700, SHA256 8e57ef5054f53174a35d906d34eab073dd6d787607cb02f29d83364ae3abc203; Git blob 495cd51581f472a9cb0a257ff7cd9f0d611dcab7. Read-only --plan succeeded once on Oct 31. Do not reinstall or repeat old jobs.
- The prior live old config SHA 66d074f32fffbf4a251576c8297714e9647174546e9e73e5bf27cf2768efe6d7 and historical PID 13546/start_ticks 100216734 are STALE, not values to pass to a new production command.
- The previously validated temporary API-enabled candidate used localhost-only HandlerService/RoutingService port 19090; it was removed, NOT installed. The installed canary generates a fresh candidate from live config and validates with xray run -test only on --trial. It is not a permanent migration installer.
- Local Termius SSH 192.168.1.1:222 without phone VPN was previously confirmed. Reconfirm immediately before interruption.
- Seven original legacy VPN endpoints vs five OpenAI-qualified pending on Nov 4; recheck health/identity before treating the pool as currently qualified. An unchanged pending file is not a running process update.

## Prepared concrete next step: one fresh NON-MUTATING live-state check

New staging code xray/staging/v30_maintenance_preflight_readonly.py (feature GitHub only; NOT installed) verifies that the on-router canary matches the EXACT prior installation checksum BEFORE importing any code. It then collects fresh old Xray PID, /proc start_ticks, boot UUID, active config SHA, watchdog and S98 identities and calls the existing pinned preflight, which reads original config/binary/backup, S97/S98/S99/wifi script hashes, SOCKS+TPROXY listener owners, firewall mark and kill switch. The script reads only, does not write any file or perform trial, rollback, guardian, signals, firewall edits or router command execution. It reports no secrets. Never fabricate current process identity from Oct 31 snapshots.

Its source-unit tests are not proof of current router status. A real on-router read-only check requires separate approval; the existing installed --plan remains a supported alternative. Do not execute the new file through Keenetic jobs in this RC43 task.

## Actual migration sequence, two DISTINCT changes

A. RECOVERABLE TRIAL, not permanent migration:
1. Fresh current read-only baseline: old Xray binary/config hash, PID/start_ticks and exclusive sockets 10808 TCP + 12345 TCP/UDP, kernel fwmark/kill switch, S97/S98/S99/watchdog/cron and the private backup manifest. Confirm the local phone can still administer the router on LAN without VPN.
2. Make an independent encrypted off-router backup to Home Assistant or another host with separately verified SSH host key, private storage, checksums and restore rehearsal. Existing router /opt is USB; /root and /etc are read-only, and /tmp is volatile. A backup in /opt cannot protect from USB loss.
3. Close the legacy root supervisor conflict: block/suspend scheduled S97/S98/S99/watchdog/cron mutations via an explicitly reviewed maintenance procedure, ensure no already-running child can use global killall or rewrite TPROXY, and verify any independent rescue process. Parent PID SIGSTOP by itself is insufficient. No global killall to stop Xray.
4. Run a separately approved PID/start_ticks-scoped 15-second canary from the correct current installed source, with the selected maintenance outage and old-session loss acknowledged. It MUST always return to legacy. Verify actual SOCKS and TPROXY TCP/UDP payloads, OpenAI (401 via SOCKS), DNS/IPv6 no-leak, fail-closed and physical recovery. If unknown, maintain fail-closed.
5. Confirm old Xray restoration and user network access, not merely a green canary log. A successful temporary trial is proof of reversible switch, not permanent promotion.

B. PERMANENT PROMOTION, separate executable and approval:
6. After the trial passes, create a versioned promotion script that changes only necessary active Xray config/init/watchdog after independent old backup and an explicit power-loss/restart rollback story. The Oct31 canary cannot be reused as promotion code because it always restores legacy.
7. Start the API-enabled Xray on existing ingress ports; verify actual live API calls (not just TCP connect), SOCKS5, TPROXY TCP and UDP, correct OpenAI-qualified pool, DNS/IPv6 and kill switch. Include a time-bounded, independently recoverable PID-scoped rollback and probe after watchdog cycles/reboot.
8. Only once promotion is confirmed may the staging-only hourly updater and dynamic pool reconciliation be considered for auto-apply under separate gates. No live automatic update enabled by RC43.

## Practical RELEASE HOLD conditions and remaining operator work

- Independently verified encrypted off-USB restore on Home Assistant: NOT DONE.
- Actual prevention of conflicting privileged S97/S98/S99/watchdog/cron children: NOT DONE. Existing canary SIGSTOP-fences two parent processes only. This is the remaining *safety* blocker; the lack of old activeConn is not.
- Fresh run of local read-only --plan or the new helper after approval: NOT DONE on Nov 7.
- Real candidate TPROXY TCP/UDP and actual rollback rehearsal: NOT DONE.
- Permanent promotion script with reviewed exact commands and independent rollback: NOT BUILT. The original canary is temporary.
- Current OpenAI-qualified pool and leak probes: require fresh measurement.

NO production migration initiated, no new Keenetic jobs, no production/main/snapshot/Cloudflare, no firewall/routes/cron changes, merge/deploy/live trial. First proceed with fresh read-only baseline and independent backup. The permanent migration must follow a real passing reversible trial. Source tests never turn these remaining physical prerequisites into claims of completion.
