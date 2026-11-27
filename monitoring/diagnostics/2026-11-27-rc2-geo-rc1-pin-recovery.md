# RC2 monitor source-pin recovery after Geo RC1 — 27 November 2026

Scope: monitoring only. No changes to Geo RC1 policy, VPN updater, Xray, watchdog, firewall, routes, kill-switch, cron or dashboard. No manual VPN probe or subscription refresh.

## Cause and compatibility
Prior acceptance: 3e58a6f6b11a5390b97649e95ff10b4e9213e0fb.
Geo RC1 report 6d96e2bbcd9ce82370afb8e1d68a4436638ecce9 and archived source 0412210e111907075a0ba25e73bd23bd466c7dda reopened. Installed updater SHA256 b65fcb96dbc9dbdb81b5e06ba48a45adaf51cc77041634f4f5b5b0be26984041 and Git blob 6770a6f9406430253e55fe460f39fcb1e4b02d29 match the documented Geo RC1 archive. Job ea622894-97aa-4872-a80e-0d6a0c5b66a7 confirmed both hashes and AST subscription definition/parser import. The archived subscription() reads the private HTTPS subscription, decodes VLESS entries and returns all entries; Geo RC1 admission filtering occurs in main(), not subscription(). create_outbound is imported from unchanged setup_xray. main() remains protected by __name__ guard. RC2 adapter invokes runpy under a different name, not updater main.

## Monitor-only change
Job c178a064-0590-460c-abd1-10443e778d00 DONE exit 0 at 20:00:19 MSK:
PINS_UPDATED changed 1 backup dynamic-source-pins.before-geo-rc1-1795798819.json.
Verified all four exact source hashes and safe regular-file owner/mode, loaded reviewed source under monitor run name and verified callable reader/parser without calling updater main. Held monitor-only probe lock, verified old pin dictionary, private backup with fsync, atomic same-directory replacement and readback. Only xray-update-v23.py digest changed (00f08d13bd653ce72a57b0f73ec046f004dca1f900a36cfcec4d254dfa2392cf -> b65fcb96dbc9dbdb81b5e06ba48a45adaf51cc77041634f4f5b0be26984041). Other three pins unchanged. Backup in /opt/etc/vpn-monitor/ mode 0600. No subscription fetch or parser conversion executed in this check; end-to-end compatibility awaits scheduled run.

## Acceptance pending
Next scheduled probe 20:03 MSK. Do not start a duplicate manual cycle. Verify actual router probe log exit 0, snapshot/cache timestamps, HA current subscription generation and all ten results, minute publication, and unchanged cron/init hashes. If updater lock causes skip or refresh failure, report rather than alter VPN. No claim of successful future cycle until evidence.
