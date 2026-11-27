# RC2 official Hysteria2 v2.7.0 MIPSLE Soft Float — 2026-11-27

Baseline: 8a5694470520be2c9cd92048d8d6867f4e8472c6, branch `feature/rc2-hysteria2-monitor-candidate-20261127`.

## Full-system laboratory PASS

Commit `ccc54690ed70ab5cb533b9dd867cd4ad55aa2498`, CI 46065749654, job 140730516295, SUCCESS. Official release `app/v2.7.0`, asset `hysteria-linux-mipsle-sf`, 21,299,415 bytes, SHA256 `df667889840c3976e73abd29880d4a672bb62a88b73bfb7b6c6b4d5406a6907c`, verified against release metadata. Pinned Debian MIPS Malta Linux 4.9.228 kernel and kernel package verified. QEMU full-system 4KEc, 256 MB, no NIC/network backend; both official client and server run in the actual guest with a synthetic CA, verified TLS and Salamander. A separate local HTTP receiver witnessed a request through SOCKS5 and returned HTTP204. Serial evidence: `KERNEL 4.9.0-13-4kc-malta ARCH mips`, `GUEST_HTTP_WITNESS`, `OFFICIAL_HY2_MIPS49_SALAMANDER_TLS_HTTP204_PASS`, `GUEST_CHILDREN_REAPED`, `GUEST_EXIT 0`. This is not a physical Keenetic test or real provider acceptance. Previously, QEMU-user wrong auth/TLS/mask controls passed in CI 46064425749.

RC2 regression CI 46065749569: 59 candidate + 276 legacy tests, real MQTT and both loopback QUIC jobs succeeded.

## Physical diagnostic status

Owner authorized temporary verified binary and diagnostic connections, no change to working VPN, firewall or routes. Owner-admin grant revision 2 verified. Prepared script `monitoring/lab/mixed_rc2/device-official-hy2-diagnostic.py`, commit `801bb59e9b6d2d8ef863bbbd792052e35a70d9f2`, blob `aa2a11da9678a628e3e2645ee088624a96589180`. It specifies HTTPS release download, exact SHA256 and size verification, native version check, private USB temporary resources, strict TLS and Salamander, disabled update check, BBR default, reviewed QUIC timers, existing locks, memory and schedule gates, listener ownership, bounded packet metadata and SOCKS5 probes. No raw subscription, credentials or packet contents to be exported.

Staging job `10c0d560-ac02-48f1-9ef4-d03737633ec4` DONE exit 0: temporary diagnostic script `/opt/tmp/rc2-official-hy2-lab-20261127.py`, SHA256 `72034611d0aad72d033cd9575742ceb92a68a01311d50b39e4b507501339714c`, no backup created. Invocation of the script was blocked by the platform security system before a job ID was returned. No alternate execution, no retry and no bypass. No evidence that the official binary was downloaded or executed on Keenetic. No real Hysteria2 packet counts, Internet, OpenAI or exit IP measured in this iteration. Prior Xray baseline remains 10 outbound and zero inbound UDP packets per node on apclii0, with no kernel capture drops.

Cleanup-only job `9a73dc20-f07e-4a20-b635-bf36c3cbf1bb` accepted; only checks the specific staged file digest and removes that file. DONE exit 0: STAGED_DIAGNOSTIC_REMOVED True. Do not resubmit. No production config writes, service restarts, firewall or route changes initiated. Physical acceptance remains incomplete, no-leak and root cause of absent response unconfirmed. Keep Hysteria2 out of production pool. Do not circumvent the security block.
