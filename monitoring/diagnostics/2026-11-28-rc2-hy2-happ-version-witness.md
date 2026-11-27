# RC2 Hysteria2 — Happ Plus version witness

Date: 2026-11-28 MSK. Baseline report commit 2bf5b84c76c6108ae09483dacbfbafa1ce19935d. Read-only research; no new device or provider tests.

## Observations

Redacted transcription of owner-provided Happ Plus Lithuania log screenshot: app v4.12.0, core Xray 26.3.27, XrayCoreStart success=true; repeated app/observatory/burst HTTP HEAD generate_204 deadline exceeded while awaiting headers, tags proxy and entry. Previous external-IP witness matched the Lithuania subscription endpoint IP. Log timestamps are transcribed without assuming the app's log timezone. The screenshot does not establish protocol, actual endpoint/port, chain topology, or successful transport handshake. Startup success is not a tunnel success witness; HTTP observatory timeouts are not specifically QUIC handshake errors.

Installed Keenetic Xray is Entware 26.2.6-1, Go 1.26.1, MIPSLE softfloat. The archived executable matched the installed SHA256 and passed isolated synthetic Hysteria2 interoperability including full-system MIPS Linux 4.9, as recorded in 63e6b1eade463dfb9f7b0117f6e3022b993a037c. Prior physical capture saw outbound UDP and no inbound packets. The actual provider profile remains unverified.

## Upstream comparison (static)

Official release: https://github.com/XTLS/Xray-core/releases/tag/v26.3.27
Compare: https://github.com/XTLS/Xray-core/compare/v26.2.6...v26.3.27 (60 commits).
- go.mod changes apernet/quic-go from v0.57.2-0.20260111184307-eec823306178 to v0.59.1-0.20260217092621-db4786c77a22 (PR 5782).
- Release documents moving QUIC configuration into finalmask.quicParams (PR 5772), adding Hysteria inbound/transport (PR 5679), and finalmask refactoring (PR 5812).
- Static compare identifies changes in transport/internet/finalmask/salamander/conn.go (131 changed lines), proxy/hysteria/client.go, and other transport code. These are candidate differences, not proof of cause. No assertion that the changed masking or QUIC code fixes the real provider failure.
- Public reports of startup crashes on MIPSLE/Keenetic with 26.3.27: https://github.com/XTLS/Xray-core/issues/5882 and https://github.com/XTLS/Xray-core/issues/5926. These reports do not establish that all builds fail, but make an untested production upgrade inappropriate.

## Decision

Do not change production VPN, Xray, firewall, routes, or updater. No new physical trial; previously blocked alternative-client launch remains blocked and must not be retried or bypassed. Profile identity and path remain unresolved; provider confirmation of actual protocol/endpoint/port and supported client versions is appropriate. Do not collect raw credentials or full unredacted logs. The owner may provide a redacted log fragment showing protocol/endpoint if available. No further phone changes are required for this report. Physical admission remains HARD NO-GO. No screenshot published in GitHub.
