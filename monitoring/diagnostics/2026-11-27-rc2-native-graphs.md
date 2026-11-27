# RC2 native graph fix — 27 November 2026

User screenshot showed configuration errors in Home Assistant iOS app, not an external browser. Registered auto-entities module was present on disk (97077 bytes) and returned HTTP 200 text/javascript from LAN HA URL; exact frontend failure is not established. Replaced custom graph cards in both vpn-openai and rc2-shadow with built-in history-graph cards, without HACS or resource changes.

Source: monitoring/homeassistant/rc2_native_graphs_apply.py, commit da5467cb5e9d638d12fc45a46d55747599b50f4a.

Live HA job 9e2f8e54-2114-4608-91ec-1f21a0d2c1d6 DONE exit 0:
NATIVE_GRAPHS 10 HISTORY 6 ENTITIES 60
NATIVE_SAVED 2 cards_per_view 20 backup rc2-before-native-graphs-1795798025.json

Both page configurations saved and read back through Lovelace API. Each current subscription node has an individual six-hour Internet and OpenAI probe-duration graph. Six grouped 24-hour history cards retained. All 60 history sensor mappings resolved. Dynamic summary/table and details preserved. Native graph entity lists are a snapshot of current inventory, active nodes ordered first at installation; a changed subscription requires rebuilding graph list. No invented measurements. iOS app rendering still requires visual confirmation. No router, VPN, cron, updater, firewall or routes changed.
