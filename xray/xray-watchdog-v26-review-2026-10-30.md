# Keenetic Xray watchdog v26: read-only review

Date: 2026-10-30
Task: 43a7b1db-19f4-4b43-b4c1-5bc9553e42ef
Result: done; exit_code=0; read_file returned complete script (truncated=false).

## Findings
- Controller implements status|plan only; no activation.
- Identity checks PID file, exact argv, process start ticks.
- Checks Xray identity using xray-identity-v24.py, requiring IDENTITY: VERIFIED and SIGNAL_SENT: NO.
- SOCKS5 check only establishes TCP connection to 127.0.0.1:10808; it does not test SOCKS handshake, VPN egress or Telegram.
- Startup check uses substring matching and can match comments.
- No explicit checks of OpenAI-qualified pool, TPROXY, fail-closed, active Xray config hash or routes.
- No migration lock, transactional activation, independent rollback timer or rollback implementation.
- Exit code 0 belongs to read_file operation, not the controller safety gate.

## Safe implementation plan (not executed)
1. Read-only inventory: capture process PID/start ticks, config.json SHA256, routing/TPROXY and kill-switch evidence, SOCKS5 handshake and tunneled egress, qualified pool membership and fallbackTag; inspect watchdog v25 and init script.
2. Prepare immutable backups and hashes of watchdog/startup and verified recovery path; design lock and exact process-identity checks.
3. Dry-run static checks and no-change safety gate. Any unknown => abort.
4. Require separate explicit approval before any switch. Do not restart Xray, modify cron/routes/kill-switch without separately authorized scope.
5. If approved later, atomically hand off watchdog supervision with a separately armed rollback; validate Xray PID and config hash unchanged, SOCKS5 Telegram through VPN, TPROXY and fail-closed, qualified pool and fallbackTag.
6. On failed validation, restore old watchdog while preserving kill-switch and fail-closed; do not silently route through ISP.

## Current action
No new router job issued. No router files, cron, routes, kill-switch or Xray process changed.