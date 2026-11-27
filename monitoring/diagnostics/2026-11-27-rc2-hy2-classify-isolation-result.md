# RC2 Hysteria2 physical classification and isolation checkpoint

Date: 2026-11-27, 20:08 UTC (23:08 MSK). Repository ment2/keenetic-vpn, branch feature/rc2-hysteria2-monitor-candidate-20261127. Predecessor report 3572822735e87d3b54547a6626f35ee5c3abdbe6; reviewed command commit eaa740cdd754c1980b38a0a4afff69c20519bae2, command Git blob ef99b8016dac25c12c6e756e0f1d114cef03e15b, owner-approved SHA256 0476f4ebb74f9ac7dd2689289df5e3e3fee138c63da7d308ed094cc21e0ec511. Exact command fetched from the pinned commit, blob and length (4048 bytes including LF) checked; submitted once with explicit owner approval. No repeat execution.

## Live evidence
Keenetic Mobile job 729016a5-b015-4307-840b-dec4ab259077, created 2026-11-27T20:08:05.000Z, DONE, exit 0. Sanitized output:

```
RECORDS 12 HYSTERIA2 2
HY 1 CLASS UNCLASSIFIED FLAG NOT_REPORTED IDENTIFIER True ASCII True
HY 2 CLASS UNCLASSIFIED FLAG NOT_REPORTED IDENTIFIER True ASCII True
SAME_EXTRA_KEYS True
TOOLS {'ip': True, 'unshare': False, 'nsenter': False, 'tcpdump': True, 'ss': False, 'strace': False}
PROC {'/proc/self/ns/net': False, '/proc/net/udp': True}
UNCHANGED True
```

Both Hysteria2 records have the same single extra key, valid ASCII identifier syntax; normalization and fixed known-name classification did not recognize it. This does not establish that it is harmless, optional or unrelated to security. No key name or value was disclosed. Earlier ECH test was negative. No parser relaxation or silent option removal authorized. Existing fail-closed candidate remains unchanged.

Installed Xray v26.2.6 native synthetic config-test previously passed with Hysteria2 and Salamander (report c9b40123ce91e4fef8edae460747e630151795a6). This is not a real provider handshake. Prior CI 46061284654 SUCCESS, 56 candidate + 276 legacy tests, real isolated MQTT and AMD64/MIPS32LE QEMU-user QUIC. No new code or tests were run in this checkpoint.

## Isolation findings and limitations
ip and tcpdump are discoverable on PATH; /proc/net/udp is present. unshare, nsenter, ss and strace are not discoverable on PATH; /proc/self/ns/net was not found. No KERNEL_FLAGS line returned, so kernel config is unknown. The results are discovery checks only, not invocation or capability tests. They do not prove that the kernel cannot implement network namespaces, nor that packet capture is permitted or complete. No socket/packet ownership or no-leak witness was collected. The previously accepted loopback-only namespace laboratory cannot be assumed reproducible on the router as-is.

## Decision and next gate
HARD NO-GO for real provider tunnel trials and deployment. Stop speculative name guessing. Obtain the provider's documented name, semantics and allowed values for the single common extra option, without sharing full URIs or credentials. If documented, implement the exact option semantics with positive/negative tests in the feature branch; if not, retain both Hysteria2 rows as unsupported. Do not ignore unknown options or weaken TLS.

In parallel, design a disposable Linux 4.9 MIPS full-system lab to investigate a process-scoped containment alternative and explicit socket/packet witnesses. Before a physical trial, separately review native kernel support and permissions, packet-capture ownership and completeness, hard failure/no-direct-fallback gates, memory/time bounds, process cleanup and unchanged baseline. Existing tools cannot yet establish that alternative. Do not install tools, modify firewall/routes/kill-switch, change namespaces on the router or submit new jobs under this approval. A live trial requires a separately approved exact command and independently verified containment; no automatic retry.

## Production scope
Read-only diagnostic only, existing pinned subscription reader invoked once, no updater main. The approved command reports unchanged hashes of active config, pending config, full-subscription snapshot and RC2 cache, and verified source pins. No change was initiated to production Xray, updater, monitoring, HA, firewall, routes, cron, pool or credentials. This is not a comprehensive new production health audit. No physical deployment, no rollback trial, no real provider tunnel test.
