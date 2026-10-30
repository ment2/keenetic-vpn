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
