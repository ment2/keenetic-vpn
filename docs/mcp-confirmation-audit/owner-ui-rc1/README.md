# Operation Consent — owner review UI RC1

Offline continuation of the archived operation-consent candidate, Git commit
`43cba1c3c066318273c91168e148a0594c9f2456`. Source-only prototype, no production changes.

## Design

- `owner-review.mjs`: deterministic validation and immutable normalized task snapshot,
  explicit review, separate transport stage, conservative 120-second deadline,
  one local delivery attempt, terminal denial/uncertainty. The approval capability
  is held only in closure memory, not returned to the screen or logged by this
  module. Actual credential handling, endpoint pinning, transport TLS, caller
  authentication and host approval are deliberately outside the prototype.
- `demo.html`, `demo.css`, `demo.mjs`: interactive owner-review mock with fixed synthetic
  fixtures. All values are displayed as escaped JSON text; no hidden truncation in
  the data. A real user click on the agreement and approval action is required by
  the mock; this is a UX check, NOT an authentication boundary. Host allow/deny
  buttons are conspicuously labeled simulations. CSP blocks outbound connections.
  No tokens, device paths or production origins are present.
- `test-owner-review.mjs`: unit tests of the new UI/client logic, using synthetic data.
- `test-browser.py`: independent Chromium UI test, no outbound requests or real
  operations. First navigation was blocked by the environment; no UI assertions ran.

## Compatibility

The historical operation consent overlay accepts literal `confirmed: true` and a
one-time `approval_id`. The prototype constructs matching JSON-RPC `tools/call`
requests for Keenetic `write_file` / `exec_command`, HA `ha_write_file` /
`ha_exec_command`, and Keenetic `queue_router_task`; the direct REST mapping uses
`POST /v1/jobs`. The injected trusted owner transport must POST the reviewed task
with `confirmed: true` to `/v1/owner/approve-operation` using separate owner-side
authentication; do not make those credentials accessible to the model. Named file
writes use the historical default 20s timeout and do not expose mode. Nondefault
write options are rejected for named/legacy routes instead of silently dropped;
direct requests preserve the reviewed mode and timeout. HA has no legacy alias.

The prototype has an in-process pending-object guard; it is **not** a proof of
remote caller identity. The baseline grant is a bearer capability bound to the task,
revision and Worker namespace, not to an independently attested remote caller or
host approval. Before deployment, implement and validate a trusted, authenticated,
server-bound pending-call handoff with short-lived consent. The client must not
return the grant in a chat message, URL, clipboard, or audit. A local cancel discards
the grant but does not revoke a server grant already issued; server expiry remains
an upper bound and explicit revoke or atomic pending cancellation is a release gate.
No direct-client fallback after a host denial or an uncertain result. On uncertainty
retain only the existing safe request/job correlation in the trusted transport and
use read-only reconciliation; never automatically reissue or resubmit.

## Run isolated tests

`node --test test-owner-review.mjs`

The browser suite requires Python Playwright and an authorized installed Chromium
(`CHROMIUM_BIN` may point to an approved binary). Run `python test-browser.py` in an
environment that allows the local test fixture. It never uses the production bridge.
Do not override administrator restrictions to run it.

New unit result: 34/34 PASS, Node 22.16.0. Browser test: BLOCKED at first navigation
(`ERR_BLOCKED_BY_ADMINISTRATOR`). Prior 37 unit + two workerd scenarios from the
baseline archive were not rerun and do not prove this UI works against live Workers.

## Release gates (all pending)

1. Attest installed Worker code and live MCP tool descriptors; do not treat archived
   SHA values as production attestation.
2. Implement remote pending-call principal binding, expiry/cancellation and a
   reviewed owner-side authentication/transport (admin and policy secrets kept out
   of ChatGPT and browser UI). Secure approval handoff is not implemented here.
3. Exercise the new adapter against both exact isolated Workerd candidates and
   update the old Keenetic console, direct clients and real MCP adapters; verify
   actual OAuth/Bearer identity and the input schema, especially legacy options.
4. Use a separate permitted synthetic test plugin with no real device access.
   Verify genuine ChatGPT confirmation UI on accept and decline, record redacted
   host evidence and queue correlation. A mock host button proves neither.
5. Verify UI in an approved browser and test cancel, expiry, altered content,
   parallel calls, wrong client and unknown outcome against the integrated stack.
6. Reuse the baseline rollback procedure in INSTALL-ROLLBACK.md, including
   policy revision/approval invalidation and completed job preservation. No live
   rollout until every gate passes and deployment is separately authorized.

OpenAI tool reference: https://developers.openai.com/plugins/reference#annotations
Annotations affect host confirmation presentation; server authorization remains
independent. No claim that this resolves a historical platform denial.
