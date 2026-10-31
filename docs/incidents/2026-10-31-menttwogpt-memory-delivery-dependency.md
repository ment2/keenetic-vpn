# Cross-project incident: MenttwoGPT Cloudflare memory delivery depends on Keenetic Xray SOCKS5

Date: 2026-10-31 (MSK). Source of truth: ChatGPT Library
`/Keenetic/Incidents/2026-10-31-menttwogpt-memory-delivery-incident.md` and
`/Telegram AI/2026-10-31-menttwogpt-memory-delivery-incident.md`.
The two existing Library records describe the same incident; do not create duplicate proposals or records.

## Confirmed incident and recovery

- Cloudflare Memory Bridge accepted memory proposals but the Keenetic Telegram synchronizer could not reach the Worker over **direct HTTPS**; TLS handshake timed out.
- The local Xray SOCKS5 endpoint `127.0.0.1:10808` could reach the Worker (unauthenticated probe correctly returned HTTP 401). HTTP proxy port 10809 was not listening.
- `/opt/etc/init.d/S96cloudflare-sync` supervises a **one-shot** `/opt/telegram-ai/cloudflare_sync.py` every **300 seconds**. The absence of a permanently running Python process is expected.
- A one-shot recovery delivered and acknowledged **5** previously queued proposals; inbox increased from **14 to 19**. All 5 had Telegram message IDs; final statuses: **2 accepted, 3 rejected**. A proposal is persisted to personal memory **only after Telegram confirmation**, never merely on Worker POST/ACK.
- Production `cloudflare_sync.py` was patched to use PySocks via `127.0.0.1:10808`, with proxy-side DNS, destination allowlisting and TLS certificate verification retained. The production smoke test exited 0 with zero new proposals and zero ACK (the backlog had already been cleared).
- **Unverified:** a subsequent successful autonomous 300-second supervisor cycle. Do not describe periodic recovery as confirmed until an independent log proves it.
- Xray config, firewall, routing, cron and Worker were **not changed** during this incident.

## Required Xray v30 migration regression gates

1. Treat local SOCKS5 `127.0.0.1:10808` as a **cross-project production dependency**, not an optional convenience. Before first API-enabled cutover, identify all clients of this port, including MenttwoGPT memory delivery and Telegram bot.
2. Preserve proxy-side DNS, TLS validation, Worker destination restrictions and fail-closed behavior. **Never add direct HTTPS fallback** when VPN/SOCKS fails; alert and retain upstream pending items instead.
3. Add an end-to-end **non-mutating** Worker HTTPS reachability probe over SOCKS with expected unauthorized response; do not send test memory proposals or ACK actual queue items.
4. Test the `S96cloudflare-sync` 300-second scheduling behavior separately from the Xray watchdog. A port cutover can temporarily strand proposals; do not trigger duplicate sends or bypass approval.
5. Require verified recovery of SOCKS ingress, real TCP/UDP and TPROXY, plus post-cutover memory-delivery observability before considering migration successful.
6. If first-cutover rollback is required, retain the **patched** SOCKS-aware sync script; restoring its pre-incident backup would restore the broken direct-TLS path.
7. Do not interpret `HTTP 401` as a failed reachability probe when deliberately testing an unauthenticated protected endpoint. Do not expose auth tokens, Worker secrets, or full memory payloads in CI.

## Source and GitHub links

- Library: `/Keenetic/Incidents/2026-10-31-menttwogpt-memory-delivery-incident.md`
- Library: `/Telegram AI/2026-10-31-menttwogpt-memory-delivery-incident.md`
- MenttwoGPT fix branch: `fix/cloudflare-memory-sync-socks5-20261031`
- MenttwoGPT incident report: https://github.com/ment2/menttwogpt/blob/fix/cloudflare-memory-sync-socks5-20261031/docs/incidents/2026-10-31-cloudflare-memory-delivery.md
- Xray v30 first migration plan: `docs/production/2026-10-31-controlled-first-api-migration-v30-plan.md`

This file documents an already applied independent production repair; **no production changes, merge, deploy or router jobs are authorized by this documentation update**.
