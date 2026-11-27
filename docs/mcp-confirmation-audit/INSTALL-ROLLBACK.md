# Exact-operation consent staging candidate

This branch contains an overlay and synthetic tests for the two Worker entry points. It is designed for an isolated checkout and local workerd. The production Worker and installed ChatGPT descriptors require separate attestation. No deployment workflow is included.

## Verified baselines

| Target | Git baseline | Input SHA-256 |
| --- | --- | --- |
| Keenetic Worker | `ment2/keenetic-control@c422f98ec4ec9b4626603a893de877ff74e161ef` | `d3020c732b2fe1faffc637a5272553dfa86e9edbb1f54599d07b06a104f4a1dd` |
| Keenetic coordinator | Same commit | `4d5516eb415e28b80011721dcf8b02ce71b8c374ffed8edd4414c643d712d2d6` |
| HA primary RC5 | `ment2/keenetic-control@a5ca752b9025f5715675931f10a3bd4de9a60457`, reconstructed by the repository's pinned RC5 workflow | `2972f8fa590b4f8ce15e9221abc34ca527cd703fd002bbf07fda657a530ba9b8` |

The entire Keenetic `worker` Git tree is identical at the tip of `fix/worker-v5-auto-unblock` checked on 2026-11-28. RC5's `stage/github-baseline.mjs` is the same Git blob as the archived HA release, `df83f16082835e8980838aeb45616aef3d1f9936`. RC5 preserves the newer OAuth changes when applying this overlay. Git hashes attest to repository contents.

## Isolated install and acceptance

1. Check out the two exact refs in disposable directories with LF line endings. Copy the pristine Keenetic `worker.mjs` and `coordinator.mjs` into a separate rollback directory. Reconstruct RC5 primary by following the local build commands in the pinned [RC5 workflow](https://github.com/ment2/keenetic-control/blob/a5ca752b9025f5715675931f10a3bd4de9a60457/.github/workflows/ha-oauth-rc5-workerd.yml). Keep the verified primary bundle as `rc5-baseline.mjs` and make a working copy named `rc5.mjs`.
2. Apply the overlay in the disposable copies. The generator aborts on mismatched hashes or unexpected source layout and copies its two sidecar modules beside the entry files.

   ```sh
   node apply-operation-consent.mjs keenetic /test/keenetic/worker/src/worker.mjs /test/keenetic/worker/src/coordinator.mjs d3020c732b2fe1faffc637a5272553dfa86e9edbb1f54599d07b06a104f4a1dd 4d5516eb415e28b80011721dcf8b02ce71b8c374ffed8edd4414c643d712d2d6
   node apply-operation-consent.mjs ha /test/ha/rc5.mjs /test/ha/rc5.mjs 2972f8fa590b4f8ce15e9221abc34ca527cd703fd002bbf07fda657a530ba9b8 2972f8fa590b4f8ce15e9221abc34ca527cd703fd002bbf07fda657a530ba9b8
   node --test test-confirmation.mjs
   node operation-runtime.test.mjs /test/rc5-stage /test/keenetic/worker/src/worker.mjs /test/ha/rc5.mjs /test/keenetic-baseline /test/ha/rc5-baseline.mjs
   ```

3. Install the RC5 stage runtime from its reviewed lockfile using `npm ci --ignore-scripts` in the stage directory before launching the last command. The harness uses synthetic credentials, local SQLite Durable Objects, loopback listeners and a stub agent. Any outbound request fails the test. It submits an agent result without touching a device or executing a shell command.
4. Before acceptance with a host, independently match the installed Worker baseline and live tool scan. Verify the host prompt and denial behavior with a harmless synthetic fixture. Verify both OAuth and legacy authorized clients, the owner-channel interaction, and all currently supported direct callers.

## Explicit owner approval

`POST /v1/owner/approve-operation` is available only with the existing admin bearer and separate policy credential. Keep both in an owner-controlled surface. That surface must show the exact task and use an explicit approval action before posting its normalized arguments with literal `confirmed: true`. The endpoint binds the capability to the operation, path or command, content, mode, timeout, policy revision and Worker namespace. It returns `approval_id`, valid for two minutes. It is a short-lived bearer capability and should be transferred only to the intended caller's pending request.

Pass that capability to the existing mutating MCP tool or jobs API for the reviewed operation. Any explicit `confirmed: false` denies the mutation. An active `owner_admin` with the correct scope may omit the assertion when exact owner consent exists. Other authorized callers must pass literal `true` as well. Boolean validation checks the wire type. Existing host prompts still apply. The server has no attestation that ChatGPT presented or received consent.

The queue accepts the capability at most once and consumes it in the same SQLite transaction that inserts the job. An existing identical request with the same idempotency key can still return its prior job. If the outcome is uncertain, use existing job recovery and do not resubmit automatically.

The previous Keenetic web console and any direct mutating clients that supply only a boolean require an update to use the owner-approval flow. The overlay implements the authenticated endpoint and MCP argument. A production owner UI, secure capability handoff and live ChatGPT acceptance are pending.

## Audit

The new owner-only `GET /v1/owner/operation-audit` returns up to 100 events from the preceding seven days. The table caps storage at 999 events and prunes expired entries on writes. It records enqueue receipt, decision, queue outcome and existing agent lifecycle events under a server-generated correlation ID. The generated ID is also available in the response header `x-operation-correlation` for requests that reach the coordinator. It carries no payload, identity, caller request ID, approval capability, job ID or secrets. A private, time-limited join inside queue storage connects lifecycle events to the correlation ID. The existing privileged administrative audit stays in place. Host-side denials and requests rejected before enqueue are outside this log's coverage.

## Rollback

1. Pause mutation traffic and resolve active or uncertain work using the existing administrative workflow. Record the current code hash and policy revision. Invalidate pending approvals by applying the approved administrative policy update before cutover. That update also cancels queued jobs, so coordinate it before taking action.
2. In the isolated namespace, restore the exact pristine Worker entry and coordinator or the pristine HA RC5 bundle. Keep the same bindings and retained SQLite state. The three new tables are additive. Baseline code ignores them. Keep persisted OAuth records and completed job state.
3. Verify the baseline tool catalog, authenticated job-result reads and policy state. Verify the new owner routes are absent. On reapplying the candidate, verify old approvals remain invalid and completed jobs have stayed terminal. Restoring baseline code also restores baseline mutation authorization behavior.

The native test executes candidate → pristine baseline → candidate against the same database and checks that a completed synthetic result survives. The live host prompt, an installed plugin rescan and a production rollback were outside this local test.
