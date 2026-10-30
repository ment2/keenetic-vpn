# Keenetic Xray v30 — preserve-current seamless pool update (design, NOT deployed)

Date: 2026-10-31. Scope: existing Keenetic Ultra KN-1810, Entware, Xray 26.2.6.
Status: design and offline verification only. **No production edits, restart, merge, deploy, firewall or cron changes.**

## User-required invariant

A periodic subscription refresh **must not cause a switch away from the currently working VPN endpoint** if that exact endpoint is still present and qualified in the new subscription. Keep established sessions. Only switch when the active endpoint fails or policy explicitly authorizes migration. Existing connections should survive when technically possible. Every eligible endpoint must be individually verified through an isolated Xray/SOCKS5 instance with OpenAI reachability (HTTP 401 is an accepted unauthenticated API response). Never use direct/freedom/provider fallback.

## Current implementation and gaps

- Production `xray-update-v23.py`: fetches subscription, constructs isolated per-outbound probes and OpenAI checks, builds `allowed`, `leastPing` balancer with `fallbackTag=allowed[0]`, and produces candidate. Current tags are positional `vpn01`, etc., so subscription reorder changes tag meaning.
- `xray-safe-hourly.sh`: validates candidate and stages `config.pending.json`; **does not apply it**.
- Production Xray: 7 VLESS outbounds, balancer `auto` / `leastPing`, observatory, no API. No confirmed hot-update support in current process.
- `S97xray` uses `killall xray`; cannot be used for zero-downtime switch. Watchdog restarts the service on local SOCKS listener loss, potentially terminating temporary probe Xray processes.
- v27 synthetic lab demonstrated a bounded outbound transition and survival of a pre-existing TCP flow, **not** real VPN handover or leastPing failover.
- v29 lab script `/opt/tmp/xray-v29-lab.sh` was prepared and hashed but historical journal does **not** confirm it was executed. Do not assume it passed.

## Correct identity and continuity model

1. Canonical endpoint fingerprint (not tag): normalized protocol, address/port, authenticated user ID, security/REALITY/TLS parameters, transport settings (WS/gRPC/XHTTP), flow, SNI and other connection-relevant parameters. Compute SHA256/HMAC; **never log or commit secrets or raw connection strings**. If credentials/transport change, treat as a different endpoint, even if hostname matches.
2. Persist stable logical outbound IDs across subscription reorder. Avoid reusing a tag for a different endpoint while live connections may reference it.
3. Track `generation`, last-known-good pool, active endpoint identity, verified_at/TTL, health status and source hashes. A `leastPing` decision does not necessarily reveal or preserve the endpoint actually serving a given connection; observe or instrument actual selection. Do not equate `fallbackTag` with the active endpoint.
4. Compute set intersection `old_qualified ∩ new_qualified`. If current endpoint remains qualified, preserve its configuration and routing selection, not merely its string tag. New verified servers become standby choices. If an existing endpoint is absent, keep old established flows during drain if architecture supports it, but never use it for new flows once disqualified.
5. Use hysteresis/cooldown and health failure thresholds; do not switch solely because a new server has lower ping. Allow controlled failover only after actual failure, then use another newly qualified endpoint. If no qualified endpoints, retain last-known-good configuration, fail closed on traffic that cannot use a working VPN.
6. Two-phase plan: prepare/validate candidate, prove activation mechanism in isolated lab, switch only **new** flows atomically, drain old flows, verify end-to-end and rollback on failure. Protect against concurrent updater/watchdog actions via lock, generation CAS, identity and start-ticks checks.

## Architecture decision required before production implementation

**Do not assume Xray supports in-process mutation of outbounds/balancer.** The current process has no configured API. Xray HandlerService/BalancerService capabilities and whether a live balancer update preserves old sessions must be verified against Xray **26.2.6** in an isolated environment. Candidate options:
- In-process API update only if the installed build and active configuration demonstrably support the exact operations and session preservation. No listener restart.
- Blue/green Xray with separate local listeners plus a stable front-end ingress and controlled new-flow redirection. Merely starting another Xray on a new port does **not** migrate the existing SOCKS/TProxy listeners or established sessions. Preserve existing process for drain and never invoke `killall xray`.

Neither approach has been validated for real production handover. Do not claim zero downtime.

## Required offline/lab acceptance tests

- Subscription reordering: same endpoints, different positions => stable IDs and active endpoint unchanged.
- One endpoint removed, active retained => no switch; add qualified standby.
- Active endpoint removed or fails => new flows move to verified standby, old sessions drain when feasible.
- Failed OpenAI, geo, invalid config, empty pool, duplicate/changed credentials => old active unchanged and fail-closed.
- Repeated concurrent refresh, stale generation, watchdog restart race, rollback, bounded cleanup.
- Real leastPing/fallback behavior and TCP/UDP continuity under controlled synthetic failures, including watchdog interaction.
- Verify zero direct/freedom fallback, no secret exposure, and no production config/iptables/cron modification.

## Next implementation stage

Implement **pure offline pool reconciliation** and behavioral tests with synthetic endpoint identities, plus a laboratory API capability probe. Keep production `xray-update-v23.py` and `xray-safe-hourly.sh` untouched. Before any deployment or live switch, require an explicit separate user approval with exact commands and rollback plan.

## Offline implementation and CI results

- Pure prototype `xray/lab/pool_reconcile_v30.py` implemented. It accepts **opaque endpoint fingerprints**, old/new pools and active endpoint. It preserves active identity when present and healthy, adds qualified standby without switching, selects replacement for new flows only on failure/removal, and holds fail-closed on empty new pool. This is a **decision policy only**; it does not reconfigure Xray, observe real active endpoint, or drain sockets.
- `tests/test_xray_pool_reconcile_v30.py`: 10 behavior tests for reordering, standby additions, removals, failed active endpoint, empty pool, invalid duplicates and first activation.
- Previous `tests/test_xray_shell_behavior.py` initially failed CI due a test-helper syntax error. Fixed without changing production files. GitHub run **41131522273** completed **success** (source contracts + updater behavior + staging/watchdog shell tests).
- GitHub run **41131576305** completed **success** for commit `a182040b90f4bb6c2105d8bd63367d707ac536f4`, including the 10 v30 policy tests. This is offline CI only, not evidence of real seamless Xray handover.

### Remaining hard blockers before deployment
1. Verify installed Xray 26.2.6 dynamic outbound/balancer API behavior and whether old TCP/UDP sessions survive a route/pool update. Current production has **no API enabled**.
2. Implement **canonical secret-safe endpoint fingerprints**, durable stable tags, live endpoint observation, last-known-good state, concurrency lock and generation CAS.
3. Prove zero direct/freedom fallback, no `killall xray`, no listener interruption, watchdog coordination and rollback under lab fault injection.
4. Obtain separate explicit approval for any live change. No production changes were performed in this phase.

## v30 REAL Xray API isolated lab: SUCCESS (CI runner, no router interaction)

Created `xray/lab/xray_v30_api_continuity.py` and branch-only GitHub Actions workflow `.github/workflows/xray-v30-isolated-lab.yml`. Workflow downloads pinned **Xray 26.2.6 linux/amd64** official release to an ephemeral GitHub runner. Router production is **linux/mipsle** and uses a different Go build; these results validate API behavior for the same Xray release, **not architecture-specific parity**.

Lab topology: one disposable Xray process, loopback-only API/SOCKS listeners on dynamically allocated ports, three local synthetic TCP echo backends A/B/C, synthetic freedom redirect outbounds **only inside the loopback lab**, blackhole catchall. No real VPN credentials, subscription or external VPN destinations. CLI `xray api bo/ado/rmo` calls are against the disposable loopback process, **not production**.

GitHub Actions:
- **41132417231 SUCCESS**: initial `bo` override A -> B; old established TCP stayed on A and continued echo; new TCP connected through B.
- **41132507202 SUCCESS**: dynamically `ado` added outbound C, `bo` selected C; new TCP used C and old A TCP still worked.
- **41132562144 SUCCESS**: after B's test socket was closed, `rmo` removed B; new TCP continued via C, old A TCP remained usable. Exact CI logs: `LAB_RESULT: PASS old TCP=A after BO; new TCP=B`, `PASS dynamic ADO outbound C; old TCP still A`, `PASS RMO drained B; new TCP=C; old TCP=A`.

During development CI initially failed due invalid catchall rule, missing observatory dependency for balancer and a Python newline syntax issue. All corrected in lab code; the final run **41132562144** completed success. The observatory is required for this configured balancer in the tested Xray 26.2.6 build; missing observatory produced `core: not all dependencies are resolved`.

### Confirmed and NOT confirmed

**Confirmed:** Dynamic HandlerService outbound addition, RoutingService balancer override, removal of an already-drained outbound, and persistence of an unrelated existing TCP stream on the original outbound without restarting the disposable Xray process.

**NOT confirmed:** real VLESS/REALITY/gRPC pool updates, leastPing observatory behavior, stable active endpoint detection, actual Telegram/OpenAI traffic, UDP/TProxy flows, deletion of an outbound **with active sessions**, zero packet loss, production API migration, production watchdog coordination or mipsle-specific behavior. The lab deliberately does not remove an outbound with active TCP flows.

**Next:** implement stable canonical endpoint fingerprint and stable tag mapping, generation-safe two-phase update, separate policy for preserving current server when still qualified; expand isolated lab with controlled failure and rollback, then review exact production migration commands for explicit approval. No merge/deploy/restart or production modifications performed.

## Stable identity prototype and 43-test offline CI

Added `xray/lab/endpoint_identity_v30.py`: canonical JSON encoding of the full VLESS outbound (excluding positional `tag`), HMAC-SHA256 using an externally provisioned **durable secret key** (minimum 32 bytes), and deterministic `vpn-<24 hex>` tag. It detects duplicate identities and tag collisions. **Prototype only**, not production canonicalizer: full outbound JSON may include non-semantic fields, key rotation changes identity, and transport normalization must be reviewed before deployment. Never commit the HMAC key or log raw canonical JSON. Changing credentials/transport correctly changes the identity.

Added `tests/test_xray_endpoint_identity_v30.py`: 10 tests for subscription reordering, tag independence, credential/host changes, duplicate rejection, key strength, unsupported protocol, key rotation and safe tags.

GitHub Actions **41132677348**: **SUCCESS**. Offline suite now includes **43 tests**: 11 static source contracts + 5 updater behavior + 7 shell staging/watchdog behavior + 10 pure pool reconciliation + 10 endpoint identity. This CI validates prototypes and frozen-source contracts, not production switching.

**Critical architectural distinction:** A stable endpoint fingerprint solves subscription reordering, **not** live balancer selection. Before deploying, observe actual selected outbound for new flows and implement a sticky policy with controlled failover; Xray `leastPing` alone can change selection without a subscription refresh. API `bo` was demonstrated in lab but must be coordinated with leastPing/fallback and actual health checks.

## Production-like leastPing lab CI SUCCESS

Expanded isolated loopback lab to run **both** `random` and `leastPing` balancer strategies against the real official Xray 26.2.6 linux/amd64 binary. GitHub Actions **41132772990** completed **SUCCESS**, with both steps successful. In each strategy, API `bo` switched new TCP A -> B, `ado` added C and redirected new TCP to C, `rmo` removed drained B, and the pre-existing TCP flow continued through A.

**Caution:** The test uses an explicit API override and synthetic loopback backends. It **does not** validate automatic leastPing selection or automatic fallback on failure, nor prove real VLESS/mipsle session continuity. This is an important positive result for the intended API-based control plane, not deployment authorization.

## Generation/CAS offline model: SUCCESS

Added `xray/lab/pool_generation_v30.py` and `tests/test_xray_pool_generation_v30.py`: 9 synthetic state-machine tests cover preservation of active endpoint, replacement on failure, empty candidate hold, failed validation/API/continuity gates and rejection of stale concurrent proposals. GitHub Actions **41132870489** completed **SUCCESS**. Offline suite now has **52 tests** (43 prior + 9 new).

The model is **in-memory only**: it is not an atomic production transaction and has no durable journal, real lock, live session metrics, automatic rollback, watchdog coordination or Xray API integration. These are required before activation.

## Controlled production migration gate (NOT APPROVED)
Current Xray process has no API. Live API-enabled handover cannot be achieved simply by applying the new staged config: a first migration of the running listener/process is required, and `S97xray` uses `killall xray`. Until an exact migration and rollback plan is approved, maintain the existing staging-only updater and working process.

Pre-approval checklist:
1. Exact source snapshot, active config hash, process identity/start ticks and backups; all secrets remain local.
2. Isolated MIPSLE Xray API/BO/ADO/RMO verification if feasible, including watchdog isolation.
3. Explicit ingress ownership plan for existing SOCKS5 10808 and TPROXY 12345, existing TCP/UDP drain, firewall/kill-switch invariants, and an expected interruption budget (cannot promise zero downtime for first API migration).
4. Lock/generation CAS, durable journal and rollback; fail-closed on invalid/empty pool or control-plane failure.
5. Exact commands and rollback script separately approved by user before any production edit, restart, merge or deploy.

At this checkpoint **no production modification, merge or deploy** was made.
