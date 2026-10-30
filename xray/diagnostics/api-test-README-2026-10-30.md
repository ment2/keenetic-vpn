# Xray v27 offline API test fixture, 2026-10-30

This is a **local-only proposed configuration**, not validated with the router binary and **not deployed**. It contains no subscription URLs, UUIDs or private keys.

- API: `127.0.0.1:18080`, `HandlerService`, `RoutingService`.
- Test SOCKS: `127.0.0.1:18081`, all requests blackholed.
- No direct/freedom outbound; no live TPROXY or VPN listener.
- Test offline only using a compatible Xray binary: `xray run -test -config api-test-config.json`.
- `api` outbound is a special Xray API handler; the JSON config declares `api.tag` and routes `api-loopback` to it. Confirm against the exact binary before any runtime test.
- Do not run on router or expose port to LAN; isolate network namespace/VM. The test does not demonstrate zero-drop switching or production readiness.

## Controlled lab tests, only after validation
1. Check no production ports are used; confirm API is bound to loopback only.
2. Query `xray api lso`, `lsrules`, `bi` using `--server=127.0.0.1:18080` in a separate lab process.
3. Add only synthetic blackhole outbound(s) via `ado`, verify with `lso`.
4. For `bo`, add an explicit synthetic balancer and route in a separate test fixture, confirm selection before and after override with `bi`; do not assume this minimal fixture has a balancer.
5. Check `rmo` on idle and busy synthetic outbounds and verify session behavior. Do not infer production semantics from successful command exit alone.
6. Test failures, rollback, and fail-closed invariants before considering a production migration.