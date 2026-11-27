# RC2 Hysteria2 option audit and native config-test preparation
2026-11-27. Branch feature/rc2-hysteria2-monitor-candidate-20261127. Prior report a5ba7fe4aed553e7406dce92b5813a7387abcc19. No production modification.

## Live approved audit
Exact command cc378a4e226aa1cc2872cfdf2770d59ca51d6c54, 3955 bytes, SHA256 bc0743c4bb1ec8d94b7e768aa855122ba6b4579412797f06e1f5d413251096e9, Git blob 544a8391b33cbb47483b4343674ce934a27e6d6c verified locally and against GitHub. Submitted once. Keenetic Mobile job b6e18b97-8ddc-47f6-9484-a9ae543ca40f created 19:55:22.525Z, DONE exit 0. Output:
```
RECORDS 12 HYSTERIA2 2
HY 1 EXTRA_NAMES [] STILL_UNKNOWN 1 DUPLICATE False OBFS_SALAMANDER True OBFS_PASSWORD_PRESENT True TLS_FLAGS []
HY 2 EXTRA_NAMES [] STILL_UNKNOWN 1 DUPLICATE False OBFS_SALAMANDER True OBFS_PASSWORD_PRESENT True TLS_FLAGS []
UNCHANGED True
```
Both use Salamander, no duplicates or recognized alternate TLS flags, one extra option per endpoint remains unidentified. Absence of recognized flags is not proof of all TLS semantics. No credentials or raw response exported. No automatic job repetition.

## Research and candidate changes
Official Hysteria2 URI specification https://www.hy2.app/docs/developers/URI-Scheme/ includes `ech` (base64 ECH config list), not covered by either previous audit allowlist. Xray v26.2.6 upstream infra/conf/transport_internet.go exposes TLSConfig.ECHConfigList as echConfigList and copies it into config.EchConfigList. Actual provider option not yet identified. Do not equate name presence or source field with interoperability; installed binary differs from official release. No ECH mapping enabled, no arbitrary option silently dropped, no weakening TLS. Commit 1896bd05ae8dd5f60f582abf43ebe1f87c4052fe adds bounded support_reason enum for unsupported_option, ech_unverified, duplicate_option, tls_policy and invalid_uri; unsupported rows remain visible but not eligible or probed. Only fixed reason strings appear in telemetry/cards; untrusted reason values sanitized. Existing VLESS identities and history contract unchanged. Three added tests cover fail-closed classification, unsafe reason redaction, HA card/history integration. Local 53 tests, 52 pass and one repository-only contract skipped; full CI below passed all.

## Regression CI
Run https://github.com/ment2/keenetic-vpn/actions/runs/46060409315 completed SUCCESS on commit 1896bd05ae8dd5f60f582abf43ebe1f87c4052fe. Unit job 140713014161: 53 mixed candidate and 276 baseline tests, all OK. MQTT job 140713014528: 12 nodes, 110 publications, 97 retained discovery and 13 nonretained states. QUIC jobs 140713014510 (MIPS32LE QEMU-user) and 140713014602 (AMD64): official archive verification, plain and Salamander four positive owned observations, wrong auth and TLS no HTTP witness, both PASS. Synthetic service endpoints, no provider or production network traffic. Not acceptance of actual physical binary.

## Next separately approved command
File rc2_hy2_native_configtest_command.txt, 4042 bytes including LF, SHA256 d7ae7673b417cab43c15d38393446c5c53d61b5b93aea771262e24c2b30bee4b, Git blob 3a85f4c00071b7960fdd1e0ec797caa1f67939cb, path monitoring/lab/mixed_rc2/device-native-configtest-command.txt in commit 1896bd05ae8dd5f60f582abf43ebe1f87c4052fe. Bash/Python syntax checked, NOT executed. One pinned reader request, safe finite option names only, ECH presence boolean, still unknown count. No arbitrary names or values exported. Check historical installed Xray SHA256, available memory >=80 MiB (conservative preliminary guard, not measured capacity proof), updater idle twice, avoid selected minute windows near cron. Then native xray run -test with synthetic loopback Hysteria2/SALAMANDER outbound, TLS enabled, no inbounds, no live tunnel, temporary private directory, synthetic credentials, bounded 10s subprocess, output code only. Check pins and unchanged production config/cache and binary at end. A success establishes config parsing only, not QUIC handshake or no-leak. If low memory, schedule conflict, unclassified parameter, native test failure or changing baseline, no further execution; do not retry automatically. Exact operation requires owner approval.

## HOLD
Physical acceptance, actual option semantics, actual native QUIC handshake, provider connectivity, independent packet/socket no-leak and cleanup rollback remain pending. No production update, Xray replacement, pool, firewall, routing, MQTT or HA change. Once option classified, review mapping against exact installed build and official spec, regress in isolated CI, then separately approve a bounded sequential native tunnel trial with production guards and independent route witnesses. No production deployment until separate acceptance.
