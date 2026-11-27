# RC2 mobile dashboard — live deployment, 27 November 2026

User approved mobile summary, ten-node table with geographic location and per-active-node latency history. Existing two Lovelace view paths vpn-openai and rc2-shadow were both updated so old links no longer present obsolete seven-node telemetry. Native Markdown and existing auto-entities/history-graph integration used; no new frontend dependencies.

Source: monitoring/homeassistant/rc2_mobile_page.yaml (commit 5aac0f575470318da3416b6ddc0456988aa8ee79), rc2_mobile_apply.py (commit 77786b8b2df6151110ab67416e6dc5e00d35f5ff).

Live HA job 193147fc-b84b-4192-a28c-0dd18e5af1ea DONE exit 0:
RENDER_PASS 10 table_lines 12 active_graphs 4
PAGE_SAVED views ['rc2-shadow', 'vpn-openai'] cards_per_view 11 other_views_unchanged True backup rc2-before-mobile-page-1795797708.json

The supported Lovelace WebSocket API saved and read back the desired configuration. Private full pre-change dashboard backup verified before save. Existing six 24-hour history cards retained; details card retains endpoint, exit IP and timestamps. Active internet probe-duration graphs show six hours of measured history, automatically follow membership. Actual measurements every 15 minutes; summary published each minute. HTTP probe duration is not ICMP RTT; failed-probe duration may also be shown. No invented measurements. Physical iPhone rendering and frontend graph drawing were not directly inspected, only live server template rendering and configuration readback.

No router, Xray, updater, watchdog, firewall, routing or cron changes. No manual probes. Dashboard: http://192.168.0.169:8123/vpn-monitor/vpn-openai .
