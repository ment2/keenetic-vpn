# 2026-10-31: Cloudflare Memory Bridge sync over Keenetic Xray SOCKS5

## Affected integration

The MenttwoGPT Cloudflare memory-proposal sync on Keenetic Ultra KN-1810 stopped receiving proposals. The Cloudflare Worker accepted the requests, but `/opt/telegram-ai/cloudflare_sync.py` attempted direct HTTPS from the router, which repeatedly timed out during TLS handshake. Cloudflare Worker and www.cloudflare.com failed directly; Google HTTPS returned HTTP 204.

The existing Xray SOCKS5 listener `127.0.0.1:10808` was healthy. A proxied unauthenticated request to the Worker returned HTTP **401**, proving a reachable TLS/HTTP path without exposing a token. The HTTP proxy at 10809 was not running and was not needed.

## Recovery and permanent application fix

- Verified router status and service logs via Keenetic Mobile owner-admin tools.
- Verified `/opt/etc/init.d/S96cloudflare-sync` has a **running shell supervisor** (PID 8951 at inspection) that invokes the one-shot Python sync every 300 seconds. No missing cron entry: this is an init.d loop, not a cron schedule.
- A temporary in-process PySocks socket adapter allowed the *unmodified* sync to recover and acknowledge five proposals: `новых = 5, повторных = 0, ACK = 5`.
- All five proposals reached the Telegram bot inbox and received Telegram message IDs, with 2 accepted and 3 rejected through the normal approval UI.
- The **MenttwoGPT application script**, not Xray, was then atomically patched to send HTTPS only for `menttwogpt-memory-bridge.wlad124650.workers.dev:443` through SOCKS5 `127.0.0.1:10808`, with `proxy_rdns=True`, allowed-destination checking, unchanged TLS certificate validation and existing secret handling.
- Production `/opt/telegram-ai/cloudflare_sync.py` SHA256 before: `fcd74c262a2796055ece3c66cfc439ea20c1964cca16f6e811120703039ddd40`.
- After: `67c80cbc03b8e18fb6145e3e975622b6e2a967431fc392ef65217464577432d5`.
- Backup: `/opt/telegram-ai/cloudflare_sync.py.bak-socks-20261031`.
- Patched-script smoke test exit 0: `новых = 0, повторных = 0, ACK = 0`. No backlog remained.
- A subsequent read-only check confirmed the new file hash and supervisor PID. A naturally scheduled success entry in the service log had **not** yet been independently confirmed at that check; don't claim this additional verification.

**No Xray config, VPN, routes, firewall, cron, Cloudflare Worker, Keenetic control agent or Telegram account settings were altered.** No deploy or merge in this GitHub repository.

## Operational lessons

1. For applications on Keenetic, distinguish direct internet reachability from the health of the local Xray SOCKS5 endpoint. An HTTPS TLS timeout does not by itself mean the Worker or bot is down.
2. Avoid building a global router routing exception for a single app when a working local SOCKS5 endpoint can be selected within that application.
3. Do not resubmit memory proposals blindly after an HTTP 202 from Cloudflare: diagnose the pending queue and local inbox first.
4. Verify the **300-second supervisor loop** and its log, not only the process name of its one-shot child.
5. Test SOCKS-unavailable fail-closed behavior, strict endpoint matching, TLS validation and no-duplicate ACK semantics.

## Source of truth

- [MenttwoGPT incident report](https://github.com/ment2/menttwogpt/blob/fix/cloudflare-memory-sync-socks5-20261031/docs/incidents/2026-10-31-cloudflare-memory-delivery.md)
- [Application code patch (isolated branch)](https://github.com/ment2/menttwogpt/blob/fix/cloudflare-memory-sync-socks5-20261031/cloudflare_sync.py)
- ChatGPT Library: `/Telegram AI/2026-10-31-menttwogpt-memory-delivery-incident.md`, `/Keenetic/Incidents/2026-10-31-menttwogpt-memory-delivery-incident.md`

This document is an integration incident cross-reference. It is not a VPN or Xray release, deploy instruction, or authorization to modify router routing.
