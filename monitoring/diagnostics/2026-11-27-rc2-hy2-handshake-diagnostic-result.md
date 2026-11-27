# RC2 Hysteria2 native handshake diagnostic — 2026-11-27

Baseline: 194fc692381f0c9c8a99af095fc092284402329e. Owner authorized real diagnostic connections to both subscription endpoints, but not production VPN, firewall or route changes. Keenetic owner_admin grant revision 2 verified. All router jobs submitted once; no automatic replay.

## Physical evidence
Read-only job a3c0d073-0a40-4ee1-a859-1a4e61469957 DONE exit 0: at 23:35:08 MSK MemAvailable 96732 KiB; updater and monitor locks idle; 140.225.199.183 and lt1.nerpvpn.net -> 212.24.109.100; route lookup succeeds via apclii0 for both. Does not prove actual packet delivery.
Capture capability job 1e68aac2-c2a2-4a0a-b6a0-8bb9b0aa6f15 DONE 0: tcpdump starts and exits normally on apclii0 and any; any reported a not-supported category (possibly promiscuous mode). No raw traffic exported.

Final native diagnostic source commit 18906fbe20e61792d1f2280202461f16de9cd566, Git blob 66de2dcdc03531b403b806937e6ac38140ef031d, device script SHA256 1874ee12ff9cdb42d83734e742a11627d54e09d7969704d3f0080e316a7f9d41. Staging job eea6c1e1-8eec-479d-8435-53e43d07cdb1 DONE 0; execution job 4ab42a7f-cab3-4ea2-8e88-af4349c38520 DONE 0. Both actual provider configurations preserved original strict TLS, Salamander and mapped QUIC settings. Sequential private SOCKS5 with blackhole default; no production pool mutation. Monitor and updater lock gates held; memory and timing gates passed.

| Observation | hy01 | hy02 |
|---|---|---|
| Resolved IPv4 endpoint | 140.225.199.183 | 212.24.109.100 |
| Route interface | apclii0 | apclii0 |
| Memory available KiB | 92780 | 91972 |
| Xray config-test | 0 | 0 |
| Owned loopback listener before and after | true | true |
| Curl exit / HTTP | 35 / 000 | 35 / 000 |
| Observed owned UDP local ports | 1 | 2 |
| Outbound UDP endpoint packets | 10 | 10 |
| Outbound packets matching observed local ports | 10 | 10 |
| Inbound UDP endpoint packets | 0 | 0 |
| Inbound packets matching observed local ports | 0 | 0 |
| Kernel capture drops | 0 | 0 |
| Xray error category | timeout: no recent network activity | timeout: no recent network activity |
| Certificate/x509/authentication error categories | 0 | 0 |

Conclusion: the immediate failure is a nonresponsive UDP/QUIC exchange at the observed route interface. No response was observed from the resolved IPv4 endpoints during the bounded captures. This is not a proof of ISP blocking, server outage, wrong mask, protocol incompatibility or complete no-leak. Local port correlation is a sampled witness, not exhaustive kernel process containment. Capture filter only covers the expected endpoints and UDP/443, so other traffic or unexpected source addresses were not evaluated. Curl 35 is not itself proof of a certificate failure. No exit IP or authenticated tunnel success. UNCHANGED True for active/pending config, RC2 subscription and probe cache, and Xray binary; temporary diagnostic script removed. No firewall or route changes initiated. No independent complete firewall/route/kill-switch audit.

## Diagnostic iteration history
v1 execution 331c2608-ab9b-4353-abc6-dfe8f513f68e: skipped by resource/schedule gate, unchanged true, script removed. v2 12d75778-cadc-44f5-a02a-ffa3476f56c8: lock contention BlockingIOError, script removed. v3 80efa5b1-b791-4c49-ac3f-007045e57637: DNS and route confirmed, assertion before valid network test, script removed. v4 ce37dd4b-413b-45ec-ab0d-a8131c6a535a: config-test 23 on both, no live handshake, unchanged true, script removed. Diagnostic filename without .json and configuration shape corrected in v5. Do not confuse these diagnostic harness failures with the provider connection failure. v5 config-tests and listener ownership passed. All five staged scripts were removed by their execution wrappers.

## Alternative client and regression
Code commit 78ac8f7c5c50c5936ab8704b1c1a666032856f35. Official Hysteria2 v2.7.0 Linux MIPSLE soft-float client SHA256 df667889840c3976e73abd29880d4a672bb62a88b73bfb7b6c6b4d5406a6907c (21299415 bytes); pinned AMD64 synthetic server. CI 46064425749 SUCCESS, job 140726192665: both digests OK, official-client positive PASS, wrong_auth PASS, wrong_tls PASS, wrong_mask PASS, OFFICIAL_MIPSLE_SF_LOOPBACK_PASS. QEMU-user in isolated loopback-only network namespace, not actual Keenetic or full-system Linux4.9. No alternative binary installed on physical router. RC2 CI 46064425658 SUCCESS: 59 candidate + 276 legacy tests, real MQTT and both loopback QUIC architectures all success. Public docs https://hy2.app/docs/getting-started/Installation/ and https://www.hy2.io/docs/advanced/Full-Client-Config/. Upstream issue https://github.com/XTLS/Xray-core/issues/5712 is similar but not a proven Xray defect: contributor reported working test with Xray 26.2.6 and Hysteria 2.7.1, issue closed not planned.

## Next gate
Compare official client against same two provider endpoints on same device using strict TLS, identical mask and auth, pinned verified binary, single temporary loopback SOCKS, bounded resources and capture. First validate official binary on disposable full-system MIPS Linux 4.9 (QEMU-user is not sufficient). Separately assess temporary binary staging, integrity, RAM, cleanup and no-leak; use owner-approved diagnostic scope only. If official client also gets no UDP response, investigate common network/endpoint path, and compare with authorized device on another network. Do not infer blocking without evidence. If official client succeeds, investigate protocol behavior differences before integrating. Production admission remains HARD NO-GO.
