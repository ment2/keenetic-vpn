# Keenetic Xray v27 — archive completeness and offline API design

Date: 2026-10-30

## Completed readbacks
The following three source reconstructions have now been uploaded successfully to ChatGPT Library `/Keenetic/Xray/sources/`:

- `setup_xray.py.readback-2026-10-30` (router task ecc2b4da-fbc3-4e46-806d-98f070621d7b)
- `xray_server_check.py.readback-2026-10-30` (router task 3939cf50-6de0-42f2-b10c-e42105e98a5a)
- `update_xray_subscription.py.readback-2026-10-30` (router task eeb3b549-8b87-4114-a603-789859eb1658)

Existing source readbacks in Library include `xray-update-v23.py`, `xray_openai_probe.py`, `xray-safe-hourly.sh`, `test-vpn-servers.py`, `xray-watchdog.sh`, `S99xray-watchdog`, `S97xray`. Historical scripts in the folder are not evidence of current router contents. Source readbacks are transcribed/reconstructed text and are **not verified byte-for-byte against router SHA256**. Source version drift after the reads is possible.

## Local verification
- Python 3 syntax compilation succeeded for all three newly reconstructed source files. No scripts were executed.
- Offline API fixture `/mnt/data/xray_v27_offline/api-test-config.json` parsed as JSON and passed static assertions: API services are HandlerService and RoutingService, inbounds listen only on 127.0.0.1, no freedom outbound.
- The fixture has NOT been validated using `xray run -test`, nor run on the router.

## Findings and security risks
- `setup_xray.py` standalone main writes live config and includes `direct` freedom outbound. **Never execute on production**.
- `update_xray_subscription.py --apply` writes live config; also redefines balancer and rules and does not ensure OpenAI qualification. **Never execute in this workflow**.
- `xray_server_check.py` starts temporary local Xray child processes when invoked; its presence in archive does not mean it is a read-only operation. It probes geo IP, not TCP/UDP continuity.
- Production Xray 26.2.6 (linux/mipsle) exposes CLI `ado`, `rmo`, `bo`, `bi`, `adrules`, `rmrules`; production API is not configured. `adrules` defaults to replacement unless `-append` is set.

## Next controlled experiment, not yet executed
1. Validate the isolated fixture with the exact Xray binary in a separate environment. Static JSON validation is insufficient.
2. In an isolated process on test-only loopback ports, test `ado`, `bo`, `bi`, `rmo`, then verify existing TCP and UDP sessions separately. Use synthetic endpoints and no production subscription secrets.
3. Test fail-closed behavior and rollback, including API unavailability and balancer override pointing to a missing tag.
4. Do not activate API in production until an explicitly approved migration and outage plan is available. The first migration may require restart and disrupt existing flows.

## Production safety
No modifications were made to router config, Xray, cron, routes, firewall, or kill-switch in this archiving step. No new router jobs were submitted.