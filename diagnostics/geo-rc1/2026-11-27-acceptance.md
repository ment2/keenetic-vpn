# Geo RC1 — scheduled acceptance, 2026-11-27

Status: installation PASS; first scheduled application PASS; full acceptance pending post-update RC2 and direct EXCLUDED_RU evidence. No production changes in acceptance.

- Installed SHA256: b65fcb96dbc9dbdb81b5e06ba48a45adaf51cc77041634f4f5b5b0be26984041. Previous updater backup SHA256: 00f08d13bd653ce72a57b0f73ec046f004dca1f900a36cfcec4d254dfa2392cf. Verified twice. Installation did not change Xray PID/configuration or force a restart.
- Tests: 16 policy cases + mixed pool + empty pool passed. Empty pool rejection is not a physical rollback test.
- Scheduled updater 19:46 MSK: APPLY then SUCCESS, 3 allowed, 1 excluded, 6 unverified. vpn10 EXCLUDED_BY, positive live evidence. Active tags vpn01 (DE), vpn07 (PL), vpn09 (US). No observed rollback in this cycle. vpn04 UNVERIFIED; previous RC2 reported RU via geo service only and API OK. Direct live EXCLUDED_RU not yet witnessed.
- HA 19:47 state OK, coverage 10/10; the underlying measurements are from the preceding 19:33 RC2 cycle. Active configs match the inventory. Four nodes had no validated exit IP. Next scheduled probe 19:48; existing scheduled acceptance 20:00 MSK, do not duplicate.
- Source archived at commit 0412210e111907075a0ba25e73bd23bd466c7dda; readback equals router staging readback. Source blob 6770a6f9406430253e55fe460f39fcb1e4b02d29.
- Incident root cause remains unconfirmed. Personal network addresses and Ray ID retained only in private library report.
- Limitations: skip/rollback may preserve an older pool; admission filtering is not continuous egress enforcement. No forced rollback or production modifications. Geolocation is service-reported; API reachability does not establish web UI availability.
