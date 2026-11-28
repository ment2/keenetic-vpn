# MCP Operation Consent RC3 — isolated owner audit and trusted transport

Parent: ment2/keenetic-vpn commit `79b85707fafe00cd74c1b4053534c72640e4203a`; archive `2026-11-28-mcp-consent-binding-rc2.zip`. All 14 listed SHA-256 values in the RC2 archive matched. No production worker, device, OAuth, firewall, installed plugin or policy was modified; no previously rejected operation was repeated. No deploy or merge.

## New behavior

The additive `owner-audit.mjs` and hash-checked `apply-owner-audit.mjs` overlay applies to both RC2 Worker entrypoints. A separate bounded private pending-ID-to-random-correlation mapping links successful registration, approval, revocation and consumption. The mapping is pruned at expiry on successful transitions, with no background deletion promise. Owner approval/revoke state transitions and their audit insertions are in the same SQLite transaction. Consumption is audited in the same transaction as job creation; failure rolls back both. A wrong owner pairing or nonrevocable request logs a standalone denied event without linking to a victim's correlation. Existing queue/lifecycle audit correlation remains separate; no job ID is exposed in the new events. The output remains {at,correlation,stage,outcome}, 100 latest events and existing 999-event/seven-day retention. Pre-coordinator authentication, malformed input, policy rejection and platform denial are not covered by this new owner transition audit. It is not complete host-side telemetry.

`trusted-transport.mjs` provides separate owner and client channel objects in one trusted process: fixed HTTPS origin, distinct owner credentials, owner credentials never included on the ordinary call, explicit owner action, allowlisted routes and signed request headers, bounded response, timeout, no redirects and no resubmission/fallback. The transport was integrated with the archived RC2 owner review and both local Workers via a synthetic fetch dispatcher. The process must remain outside model access. The caller still must integrate a genuinely authenticated host invocation path and independent owner pairing; the code cannot attest that the ChatGPT confirmation dialog occurred. The current installed adapters and live OAuth/Bearer identity remain unverified. No credentials in the archive.

## Evidence

- Reconstructed exact archived HA primary (`2972f8fa590b4f8ce15e9221abc34ca527cd703fd002bbf07fda657a530ba9b8`) and five Keenetic core Git blobs, then applied the archived RC1 and RC2 overlays. RC2 three output SHA-256 values matched the documented values. Keenetic legacy catalog remains a synthetic stub, not the original console.
- New local integration: 8/8 subtests across two real source builds on Node 22.16.0 and SQLite (10/10 TAP including two parents). Registration/approval/revoke, mismatched key and duplicate revoke, actual signed transport wiring, revoke/enqueue race and redacted audit. `owner-audit-integration.tap`.
- New transport tests 6/6 PASS; synthetic plugin protocol tests 2/2 PASS. 16 substantive tests total (18 TAP including parents). Earlier RC2 acceptance was not repeated.
- Native workerd: BLOCKED, not PASS. Pinned package-lock SHA-256 `9920663ac095b9f382d5d2db06f1a9422fc72369d3ef895dbc8ba1463413374b`. Offline npm ci failed ENOTCACHED (youch-core); regular npm ci timed out; the native test invocation failed MODULE_NOT_FOUND for miniflare before any test executed. `native-runtime-check.txt` and `native-attempt.txt`. No bypass, alternate download mirrors, or unapproved browser access. Native runner prepared but not certified.
- Synthetic Consent Lab: source, portable identity manifest and tested in-memory MCP fixture under `synthetic-plugin/`. No device, file, shell, network or production data access. Not registered/connected; no approved separate HTTPS test endpoint is available. The host allow/deny UI was not tested. No old browser restriction retried. See its README for a genuine isolated host acceptance procedure.

## Reproduction (disposable checkout only)

Extract the parent RC2 archive to BASE and this RC3 package to HERE. Reconstruct the isolated build using the exact commands and input hashes from BASE/owner-binding-rc2/README.md. The RC2 output hashes must be:

- Keenetic entry `667c25d33ec7848beaf6128d869b8fbd73a3624e3897b22dd9107fc76126e831`
- Keenetic coordinator `b6d682683d395a53611289a39488a5b108c064a534c7bc4fc62654da753c93e8`
- HA entry `979d6e863179c43acc8930f21ff8e05e6917123c0436f5112a5d79c40b22d8f8`

Apply only in the disposable STAGE directory:

```
node "$HERE/apply-owner-audit.mjs" keenetic "$STAGE/keenetic/worker/src/worker.mjs" "$STAGE/keenetic/worker/src/coordinator.mjs" 667c25d33ec7848beaf6128d869b8fbd73a3624e3897b22dd9107fc76126e831 b6d682683d395a53611289a39488a5b108c064a534c7bc4fc62654da753c93e8
node "$HERE/apply-owner-audit.mjs" ha "$STAGE/ha/rc5.mjs" "$STAGE/ha/rc5.mjs" 979d6e863179c43acc8930f21ff8e05e6917123c0436f5112a5d79c40b22d8f8 979d6e863179c43acc8930f21ff8e05e6917123c0436f5112a5d79c40b22d8f8
node "$HERE/owner-audit-integration.test.mjs" local "$STAGE/keenetic/worker/src/worker.mjs" "$STAGE/ha/rc5.mjs"
node --test "$HERE/trusted-transport.test.mjs" "$HERE/synthetic-plugin/test-fixture.mjs"
```

RC3 outputs: Keenetic entry unchanged; coordinator `bce342a8dc1712813ca736b1f9d7ee85467ebf926876209b07ff8d183aa8970e`; HA entry `32a202bde7ee08b1806eac8d8809e605cee497e7d2aba8d72548150c3e1f8645`. Archive contains pinned package.json/package-lock.json. On an approved isolated runner, install from lock via `npm ci --ignore-scripts --no-audit --no-fund` and execute:

```
node "$HERE/owner-audit-integration.test.mjs" native "$STAGE/keenetic/worker/src/worker.mjs" "$STAGE/ha/rc5.mjs" "$HERE"
```

The native runner uses Miniflare pinned versions, SQLite DOs, loopback and outbound denial. Must verify native behavior, rollback/reapply and exact source with original Keenetic legacy console. Do not equate local Node SQLite with workerd. Before release, attest actual deployed versions and live descriptors; independently verify owner authentication and transport pairing, native API behavior, actual host accept/decline and OAuth clients, no direct fallback after host refusal. Production status NO-GO.

## Rollback

Only after approved maintenance, quiesce mutations, reconcile existing work without replay, invalidate all pending grants via policy revision with existing queued-job cancellation semantics. In disposable tests restore exact RC2 modules with unchanged SQLite storage; new owner audit table is additive and RC2 ignores it. Verify completed jobs, state, audit history, and old approvals invalid before reapplying. No database deletion. Real deployment or native rollback not tested in RC3.

OpenAI docs: https://developers.openai.com/plugins/reference#annotations — annotations affect host presentation, not server authority.
