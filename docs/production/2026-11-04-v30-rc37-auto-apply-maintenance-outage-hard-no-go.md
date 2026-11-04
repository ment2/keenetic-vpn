# RC37: owner-approved outage, correct pool comparison, production gate

Date: 2026-11-04. Project: ment2/keenetic-vpn. ONLY branch:
`feature/xray-v30-stable-tcp-ingress-lab-20261031`.

## Owner instruction
Owner wants the newly OpenAI-qualified pool automatically applied when it *differs from the actual live pool*, and no operation when it has not changed. Owner also permits temporary VPN interruption if necessary, but has not separately stated that losing every pre-existing TCP/UDP session is acceptable or that physical rescue has been independently proven.

## Verified facts
- Legacy Xray PID 13546 (last confirmed), API absent; active on-disk config has seven outbounds: vpn01, vpn02, vpn04, vpn05, vpn06, vpn07, vpn09. Verified candidate contains five: vpn01, vpn02, vpn04, vpn05, vpn09; vpn06/vpn07 failed isolated OpenAI checks.
- Active `xray-safe-hourly.sh` is expressly `STAGED_ONLY`: candidate validation writes `config.pending.json` and never applies. `PENDING_UNCHANGED` cannot imply the live Xray is updated. No pending or production files modified by RC37.
- S97xray uses `killall xray`; watchdog invokes S97 restart on missing SOCKS port; S98 packet rewrite and root cron/descendant fencing are not independent. RC36 shows private UDP worker association can survive kernel conntrack expiry, so pinning by conntrack alone is unsafe.
- The existing RC36 v30 branch has real MIPS/Linux4.9 QEMU evidence of some TCP/UDP ownership preservation and fatal safety-counterexamples. Production remains HARD NO-GO. Historical offline baseline had 729 tests at source-specific SHA, not a physical release.

## RC37 implementation in existing v30 branch
- `xray/lab/rc37_live_vs_pending_candidate_gate.py`: pure offline semantic comparison of live, pending, candidate. Returns APPLY_REQUIRED_BUT_BLOCKED when live differs even if pending equals candidate. Compares VLESS endpoint transport and client credentials, catches tag reuse, empty pool and invalid fallback, refuses claiming active endpoint identity without runtime evidence. When disk files are equal but active process cannot be attested, returns DISK_UNCHANGED_RUNTIME_UNVERIFIED rather than silently SKIP_UNCHANGED. No shell commands, physical authorization or credential output.
- `xray/lab/rc37_maintenance_window_release_gate.py`: deliberately separate owner-outage option from original seamless invariant. An outage does not imply permission to lose active sessions, and even all synthetic booleans cannot authorize production. Requires independently proven rescue, root watchdog fencing, PID/start-ticks/boot ID, target-kernel API candidate, fail-closed DNS/IPv6, durable CAS, rollback and full SOCKS/TPROXY TCP+UDP readiness.
- New tests: `tests/test_xray_v30_rc37_live_vs_pending_candidate_gate.py`, `tests/test_xray_v30_rc37_maintenance_window_release_gate.py`.
- GitHub Actions `Xray snapshot offline source contracts`: **SUCCESS, 752/752 tests**, run https://github.com/ment2/keenetic-vpn/actions/runs/41814237742, exact source SHA `52f3a04260e9459a4407e80386d34e9850f58cbb`. Earlier intermediate runs: 41813826095 SUCCESS; 41813986574 SUCCESS, 750/750 tests. These are offline/source-contract tests only.

## Decision and next order
1. Do NOT enable an auto-apply cron edit, S97 restart, killall or physical Xray cutover. The RC36 HARD_NO_GO_PRODUCTION still applies.
2. Keep OpenAI validation strict (v23 updater proves five eligible) and keep the known pending config as a candidate only. Expose active/pending divergence as a monitoring alert; never label seven active endpoints all OpenAI-qualified.
3. Physical first migration to API-enabled Xray: separately validate an independent off-USB recovery path, complete root S97/S98/S99/watchdog/cron descendant fencing (advisory flock alone is insufficient), capture exact process identities/config SHA+boot generation, ensure no-direct fail-closed and exact rollback. Any permitted interruption must have its own explicit session-loss policy and reviewed exact commands.
4. After first API migration, use existing `pool_reconcile_v30.py` and `pool_generation_v30.py` with proven real API interactions and process/session owner witnesses. Preserve the verified current endpoint; route new connections only to qualified endpoints; drain existing sessions; never reuse vpnNN tags across changed endpoints in-place.
5. Full uninterrupted UDP/TPROXY preservation requires authoritative Xray UDP owner inventory + atomic ingress freeze/commit; RC36 explicitly proves this missing. If the owner chooses a maintenance migration allowing old-session loss, document that downgrade of continuity guarantee and test it separately.

**No production, main, snapshot, Cloudflare, actual firewall, routes, Xray process, watchdog, cron, or merge/deploy touched in this RC37 stage.**
