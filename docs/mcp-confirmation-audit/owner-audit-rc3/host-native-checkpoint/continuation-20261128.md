# MCP Operation Consent RC3 continuation — 2026-11-28

Parent checkpoint: `ment2/keenetic-vpn@c1575fca78e967f136140b9c0388cd07823a8e46`.

## Completed in this continuation

- Retrieved `/Keenetic/Xray/2026-11-28-consent-rc3-host-native-checkpoint.zip` from the Library. Archive SHA-256: `8a6e2149cdf96baa5090c71e1061521d9b08c465a64ac0cb5b782161c2428986`. All 12 payload entries match the included `SHA256SUMS`.
- Retrieved the exact legacy reference from `ment2/keenetic-control@c422f98ec4ec9b4626603a893de877ff74e161ef`; `worker/reference/worker-v4.js` has Git blob `64e9ae80553852a4ee77c290db13da2e8fa7fc1a`. This resolves the missing-source prerequisite, but does not itself execute the native harness.
- Created and privately published a separate Synthetic Consent Lab Site with an MCP server. HTTPS URL: https://synthetic-consent-lab-vlad-20261128.crxqh9h5cc.chatgpt.site
- The Site access policy is custom/owner-only (only the owner's account is listed). Its MCP publication reports `has_mcp=true`; the generated private plugin ID is `plugin_asdk_app_sites_c6a48820fcb48191a9d2aea79fcdaaa8`. Plugin Management reports it is already installed.
- The Site uses the checkpoint's unchanged synthetic `server.mjs` fixture (SHA-256 `8810679ef1dae9ad136ab98a5f18a15bfd937bf08e9baff6ad61b0811070a75d`) plus a small Site MCP protocol adapter. The adapter exposes only the two fixture tools and handles Site MCP discovery/initialization. The fixture has only an in-memory ALPHA/BETA marker; no device, shell, file, production binding, credential, or outbound call.
- Final Site source commit: `80bf95314faec1ed73a07c995d155b918948ed32`. Published deployment `appgdep_6b0a80409fa08191a251a29a5225f09c` succeeded. A first package attempt failed because the server entrypoint referenced a source file outside the hosted bundle; the exact fixture was copied into `dist/server`, the import was corrected, and the same private Site then deployed successfully.
- `node --check` passed for the deployed fixture and adapter files.

## Still blocked / not claimed as passed

- Native RC3 workerd acceptance and native rollback were not run. The checkpoint records the pinned `miniflare`/ `workerd` packages unavailable and prior installation attempts blocked. In this continuation, `workerd` was still absent from PATH and the project-local package directories/cache were absent. No dependency installation, alternate mirror, or bypass was attempted.
- The current conversation has no Synthetic Consent Lab tool binding. The standard install suggestion returned “Already installed”, but no fixture tools appeared in this conversation. Therefore no ChatGPT host confirmation prompt was generated: neither a real denial nor a real approval was tested, and no mutation was sent to the fixture.
- The hosted MCP endpoint has not yet been exercised through the plugin tools. Successful Site publication and `has_mcp=true` establish deployment, not a successful host tool call.
- Previously completed loopback TLS, packaging, and local browser UI tests were not repeated.

## Production boundary and next step

No router, production Worker, OAuth, firewall, production policy, or existing plugin was changed. The new Site is separate and owner-only. RC3 remains NO-GO until native workerd/rollback evidence and real host accept/deny evidence are collected.

To continue the host test, open a fresh chat with the already-installed **Synthetic Consent Lab** plugin selected. First call `synthetic_status` (expected ALPHA / 0), request BETA and decline the actual host confirmation, then call status again (must remain ALPHA / 0). In a separate request, approve the actual host confirmation once, then verify status is BETA / 1. If the confirmation prompt is unavailable or refused by the host, stop and record that result; do not substitute a direct protocol call.
