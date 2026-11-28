# RC3 native acceptance and Backup DR gate — 2026-11-28

## Decision

**RC3 native acceptance: PASS. Native rollback/reapply: PASS. RC3 release: NO-GO. Backup DR: HOLD.** The isolated GitHub Actions run passed both native gates. Production Worker, router, Home Assistant service, policy, plugin, and deployment state were not changed.

## Checkpoint and exact inputs

- RC3 source: `ment2/keenetic-vpn@c1575fca78e967f136140b9c0388cd07823a8e46`.
- Legacy Keenetic reference: `ment2/keenetic-control@c422f98ec4ec9b4626603a893de877ff74e161ef`, Git blob `64e9ae80553852a4ee77c290db13da2e8fa7fc1a`.
- Reconstructed RC6/RC2/RC3 sources and pinned sidecars passed the preflight hashes. Native package lock SHA-256: `9920663ac095b9f382d5d2db06f1a9422fc72369d3ef895dbc8ba1463413374b`; Miniflare `5.20261123.1-beta`, workerd `1.20261123.1`.
- Final GitHub Actions run `46124288069`, job `140915306692`, commit `7e05b773c1d62b081e905177f670be52987b0c0f`; evidence artifact `15255416343` (30-day retention). The branch is `codex/consent-rc3-native-rollback-20261128` in `ment2/keenetic-control`.

## Native acceptance and rollback

- Existing RC3 native integration harness passed on GitHub-hosted Ubuntu with the pinned Workerd runtime: **10/10 tests**, 0 failures. Both Keenetic and HA Worker builds passed 4/4 subtests: correlated approval/revoke audit, invalid proof and owner pairing rejection, signed transport consumption, and revoke-versus-consume race plus redaction checks. The test host denies outbound calls and uses synthetic bindings and SQLite Durable Objects.
- Separate native rollback/reapply passed **2/2**: RC3 → exact RC2 → RC3 for Keenetic and HA using the same temporary SQLite Durable Object persistence path. A completed synthetic job remained `done`; the legacy audit route remained available during rollback; the owner-audit table/events were preserved after reapply (`audit_preserved=8` per target); a policy revision invalidated a pending test grant.
- The prior Work UI BETA/1 operation was **not repeated**. These were isolated Workerd fixtures with their own synthetic operations and disposable state; no live endpoints were contacted.

## Current working MCP compatibility

Read-only permission metadata: Keenetic revision 2 and HA revision 4; remote/admin enabled; scopes `diagnostic`, `exec`, `read_file`, `write_file`. This is an administrative grant, not host-consent evidence.

The current write tools remain legacy contracts: Keenetic `queue_router_task` and HA `ha_exec_command` / `ha_write_file` accept optional `confirmed?: boolean`. They do not carry RC3 pending-operation registration, challenge-bound owner approval/revocation, or the signed one-time transport proof. **The current MCP adapters are not compatible with RC3 as a released consent path.** No write call was made.

## Backup DR decision and remaining gates

The original gate at commit `ment2/keenetic-vpn@4af0362b459fea39bd3e850a8028293b7873e8f1` still forbids repeating or routing around the previously rejected Keenetic package transfer. The new GitHub workflow was test-only (`contents: read`), with no deployment step. It does not establish an approved sender installation route. Commit `4af0362b459fea39bd3e850a8028293b7873e8f1` was not used to install or activate anything.

RC3 remains NO-GO and Backup DR remains HOLD until the separately required host integration and real install gates are met. In particular, the reported BETA/1 run had no additional host confirmation window; it cannot stand in for an independent accept/decline test, and it was not repeated. The current adapters also lack the RC3 transport. The sender install path must be established through the previously authorized normal route; no alternate tool, host, or transfer method was used.

No operational master/escrow key was created; no owner-reviewed allowlist, sender, schedule, archive, receipt, or isolated restore was activated. Existing receiver staging `17/17` and synthetic restore PASS remain historical evidence and were not rerun.

## Evidence links

- [Successful native acceptance and rollback run](https://github.com/ment2/keenetic-control/actions/runs/46124288069)
- [Isolated runner branch](https://github.com/ment2/keenetic-control/tree/codex/consent-rc3-native-rollback-20261128)
