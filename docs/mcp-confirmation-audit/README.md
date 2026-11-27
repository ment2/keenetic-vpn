# MCP write authorization: offline contract and audit candidate

This standalone sample is not a deployed plugin, a Worker patch, or a mechanism to approve a host action. It implements no network or filesystem writes. The OpenAI documentation at https://developers.openai.com/plugins/reference#annotations distinguishes tool annotations from server-side authorization. `destructiveHint:true` indicates a potentially destructive action for which the host should elicit explicit approval. It is not a server-side permit. An application-specific boolean is merely a caller assertion, not a verifiable receipt of host approval.

## Proposed changes

- Preserve all four write annotations, including `destructiveHint:true` and `openWorldHint:true`.
- Clarify that `confirmed:true` may only be supplied after explicit approval of the exact operation, never inferred from a standing administrative grant. Do not retry rejected or uncertain operations.
- For valid policy and boolean/omitted arguments, preserve the historical server decision: remote enabled and matching scope required; a standing owner grant or a caller assertion is additionally required. Malformed confirmation arguments fail closed. No grant expansion.
- Record a bounded, structured decision event with server-generated correlation ID, policy revision, decision, and presence/state of the confirmation argument. Do not log paths, contents, command arguments, auth headers, secrets, or claims of verified host approval. A server log can only describe a request actually received.

## Test

`node --test test-confirmation.mjs`

37 isolated tests pass, including 24 combinations of the historical authorization predicate, malformed inputs, unchanged annotations, and audit shape. These are unit tests, not a physical or end-to-end integration test. The candidate assumes an authenticated request and schema-validated inputs, a trusted policy read, and a server-generated correlation ID. It does not establish that a previous rejection occurred at the host, or cure such a rejection. Before integrating, verify actual deployed source and tool descriptors, preserve all authentication/scope/path/content checks and policy transaction boundaries, add end-to-end tests with synthetic non-destructive fixtures, validate audit storage bounds and retention, review host approval behavior, and use an independently approved release process. No production changes.
