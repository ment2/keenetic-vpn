# RC3 native acceptance and Backup DR gate — 2026-11-28

## Decision

**MCP Operation Consent RC3: NO-GO. Backup DR: HOLD.** The requested native acceptance and rollback could not be run because this Work session has no approved native runner available. Backup DR did not proceed past the existing installation gate. No production Worker, router, Home Assistant service, policy, or plugin was changed.

## Checkpoint and fixture

- Parent requested: `ment2/keenetic-vpn@c1575fca78e967f136140b9c0388cd07823a8e46`; the referenced RC3 README is readable at that ref.
- The supplied host-native checkpoint archive was extracted and all 12 listed payload hashes in `SHA256SUMS` passed.
- The recorded synthetic result remains **BETA / 1**. It was not repeated. No additional host confirmation window was observed, so this is evidence of one successful synthetic mutation only; host-side decline and distinct confirmation evidence are still missing.
- The exact legacy Keenetic reference was retrieved from `ment2/keenetic-control@c422f98ec4ec9b4626603a893de877ff74e161ef`; Git blob: `64e9ae80553852a4ee77c290db13da2e8fa7fc1a`.

## Native runner gate

The current Work shell reports Node `v24.22.3` and npm `11.19.1`, but neither pinned `miniflare@5.20261123.1-beta` nor `workerd@1.20261123.1` is installed; `workerd` is absent from PATH. The checkpoint already records blocked package installation in its prior environment. This session exposes no existing GitHub Actions run for commit c1575fca, and no runner dispatch interface was available. No package install, mirror, alternate transport, or retry of the denied operation was attempted.

Therefore the native RC3 harness, native rollback/reapply, and their isolation/SQLite checks remain **NOT RUN**. Loopback HTTPS and packaging tests in the checkpoint do not substitute for workerd acceptance.

## Current MCP compatibility

Read-only permission metadata still reports Keenetic revision 2 and Home Assistant revision 4, both with remote/admin enabled and diagnostic/exec/read_file/write_file scopes. This is an administrative grant, not proof of host consent.

The active write descriptors remain legacy-style:
- Keenetic `queue_router_task`: `op`, optional command/path/content, optional `confirmed`.
- Home Assistant `ha_exec_command` and `ha_write_file`: command or path/content plus optional `confirmed`.

They do not expose the RC3 pending-client registration, challenge-bound owner approval/revocation, signed one-time consumption proof, or the authenticated transport-header contract. RC3 is therefore not compatible with the currently exposed write tools as a released consent path. No write call was made.

## Backup DR decision

The existing Backup DR gate still forbids repeating or rerouting the rejected Keenetic package transfer. Permission metadata does not establish an allowed sender installation path. The required independently approved runner and штатный путь установки were not established, so commit `4af0362b459fea39bd3e850a8028293b7873e8f1` was **not** used to install or activate anything.

No operational master/escrow key was created; no sender, receiver, schedule, or archive was activated; no HA or router change was made. Existing receiver staging and synthetic restore evidence remain historical and were not rerun.

## Release gates still open

1. Run the pinned RC3 native harness and rollback/reapply on an explicitly permitted isolated runner using the exact compiled sources and legacy reference.
2. Establish actual host-side accept and decline evidence without repeating BETA/1, then verify that refusal does not reach the fixture.
3. Attest deployed descriptors, transport identity, and client compatibility; the active MCP contracts currently do not implement RC3.
4. Independently establish an allowed Backup DR installation path without repeating or routing around the rejected transfer.
5. Only after the gates pass, resume the frozen Backup DR runbook and perform its owner-reviewed allowlist, key/escrow, first archive, receipt, and isolated restore gates.

No release gate is marked passed based on a synthetic tool result or permission grant.

## Follow-up after user authorization

- The exact RC2 and RC3 source archives are available and were inspected; they contain pinned manifests and test harnesses, not a native runtime or preinstalled packages.
- A read-only search of the current runtime, system package paths and workspace found no `workerd` executable or installed `miniflare`/`workerd` packages. The local npm cache has no matching package entries.
- The current Work shell is not established as the project-approved native runner. Existing GitHub Actions runs remain empty for the pinned commit, and the available GitHub actions tools do not expose workflow dispatch. No package installation or alternate download route was attempted.
- User authorized continuation, but that permission does not provision a runner. Native acceptance and rollback remain blocked until an authorized runner is connected or exposed.
