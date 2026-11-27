# RC2 24-hour history legends — 2026-11-27

Server installation and config readback PASS; browser visual acceptance PENDING.

- Source commit 8e63efb63b11fa05321e29d540c03617e0161b0b, blob 1ab245470bbebf35d16cdeea2b9a3498eacca1b8. Home Assistant frontend version 20261028.6.
- Existing HA job f1fe05f7-7608-4cb9-8374-c78a0bf01f1e, exit 0, not resubmitted: LEGEND_APPLIED 4, native_graphs_preserved 4, other_cards_unchanged 16, other_views_unchanged 1.
- Scope: vpn-monitor/rc2-shadow, four native 24h history graphs (VPN, internet, OpenAI, geo), each wrapped by custom:rc2-history-legend. The wrapper derives swatches from native rendered segment data rather than assuming a static state palette. All four original graph configurations remain intact. Numeric timing cards remain native.
- Resource /local/rc2-history-legend-v1.js?v=8e63efb6 registered as module, resource ID ff99eb8d413f4fc89cb11bb267410b00. Local HTTP 200, SHA256 3acd070e9c3691016f3ffbe94fa314235109fdbcd0e9b3d3276dc0d16a007587. Previous mocked legend extraction checks passed (3 cases). Configuration readback digest d53c7e644e2690d477177a7a258320b5035b104c475cb5fe7eb2c7130db7a09f.
- Backup rc2-before-history-legend-1795799723.json in HA agent directory, original dashboard plus resources, mode 0600, verified on write. Rollback not exercised. If needed, compare current configuration and restore only four cards via Lovelace API; remove only the added resource after verifying references.
- Browser visual execution is not established by HTTP/readback or mocks. Existing browser connection unavailable. Refresh dashboard on iPhone and confirm four legends and graphs; compare state tooltips with displayed swatches. Recheck after HA frontend updates because wrapper depends on native component structure.
- No changes to VPN, Xray, updater, collectors, sensors, firewall or cron. No new HA job submitted in this result retrieval turn.
