# Keenetic Mobile integration

## Components
1. **Keenetic Ultra KN-1810**: Entware and Xray; local SOCKS5 endpoint `127.0.0.1:10808`, Xray configuration under `/opt/etc/xray/`.
2. **Keenetic Mobile Agent**: router-side agent polls the Cloudflare bridge for queued jobs and publishes results. Source of truth: [ment2/keenetic-control](https://github.com/ment2/keenetic-control).
3. **Cloudflare Worker**: queue/control plane for diagnostics and authorized router operations, not the VPN data plane.
4. **ChatGPT**: requests diagnostics through the plugin; does not directly forward VPN traffic.

## Boundaries
The Worker is a management bridge. VPN packets traverse the router/Xray and configured upstreams, **not** the Worker. The router agent's queue/receipt lifecycle is independent from Xray runtime. Do not infer successful application of a change from a queued job; inspect its final result and verify router state.

## Safe workflow
- Inspect archived scripts, check hashes, and run offline/static validation first.
- Submit router operations only with explicit authorization and an exact command; avoid duplicate jobs while queued/running.
- For laboratory experiments use isolated ports and synthetic endpoints; confirm cleanup.
- Before and after any separately approved production change verify Xray PID, SHA256 of active config, SOCKS5 health, cron and routing/killswitch state.
- Never expose subscription URLs, UUIDs, tokens or private keys in logs, reports or GitHub.

## Version caveat
The archive includes v23–v29 experiments and snapshots, not a verified declaration that every archived file is the current installed production file. In particular v29 journal is a historical snapshot; check current job results before stating whether its lab ran.
