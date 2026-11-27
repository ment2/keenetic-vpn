# RC2 Hysteria2 native config-test — 2026-11-27

Baseline 3130a811c19eb4268caff5201df96af24f3d8957; candidate CI 46060409315 SUCCESS (329 tests, MQTT and two QUIC labs). Branch feature/rc2-hysteria2-monitor-candidate-20261127.

## Authorized physical check
Exact command from 1896bd05ae8dd5f60f582abf43ebe1f87c4052fe, 4042 bytes incl LF, SHA256 d7ae7673b417cab43c15d38393446c5c53d61b5b93aea771262e24c2b30bee4b and blob 3a85f4c00071b7960fdd1e0ec797caa1f67939cb locally verified. Submitted exactly once, Keenetic Mobile job bd4c186b-9bf2-4e4b-a4b7-4bc0017a63b4 created 20:00:31.204Z, DONE exit 0. No automatic repetition.

```
RECORDS 12 HYSTERIA2 2
HY 1 KNOWN_EXTRA_NAMES [] STILL_UNKNOWN 1 DUPLICATE False ECH_PRESENT False
HY 2 KNOWN_EXTRA_NAMES [] STILL_UNKNOWN 1 DUPLICATE False ECH_PRESENT False
MEM_AVAILABLE_KIB 90708
NATIVE_CONFIG_TEST_EXIT 0
UNCHANGED True BINARY_UNCHANGED True
```

Native installed Xray SHA256 680db07db2b5d53080bfecb8752bc830c6a890367aa3bc57d42d4660506591f2, matches historical baseline, differs from upstream archive extracted binary. Native synthetic Hysteria2+Salamander config accepted by `run -test` under resource guard, 90,708 KiB available (88.58 MiB). No live listener, no real provider tunnel or authenticated HTTP/QUIC session tested. ECH lowercase query key absent on both; not a test of ECH implementation. Upstream Xray v26.2.6 hysteria/dialer.go uses tlsConfig.GetTLSConfig and quic.DialEarly; TLS config.go calls ApplyECH for configured ECH values. Official Hysteria2 URI spec https://www.hy2.app/docs/developers/URI-Scheme/ defines ech as config list. No ECH mapping required by currently observed records. One unclassified parameter remains per entry; never silently drop it. No change to production, updater, RC2, VPN or firewall initiated. UNCHANGED applies to checked files, not a comprehensive integrity attestation.

## Next diagnostic — separately approved, not submitted
rc2_hy2_safe_key_audit_command.txt: 4095 bytes including LF, SHA256 9f1ee657799ba147c138d20b06600d36a555abaed6a2ce38b1b19db13a54f687, blob fd4da9fc746b49e0924d3e699ce1dacd5f1e79b9. Reuses pinned reader, updater-idle witness, single provider fetch and file equality guard. Instead of repeated exact-name guessing, only outputs names of unclassified options with ASCII identifier syntax, maximum length 32, dictionary segmentation into conventional configuration terms, and no overlap with auth/query values of length >=4. Values, raw URI, private tokens, digests and exception details never printed. This is a conservative filter, not a guarantee of recognizing arbitrary names; masked names remain a blocker. Shell/Python syntax checks and 12 isolated tests of safe_name passed. No parser change or new network probe. Separate owner approval required.

## Physical test plan (HARD NO-GO until gates)
1. Classify real option, review its semantics, preserve TLS verification, adapt candidate only if necessary, regress in isolated CI. Unknown/unsafe options remain unsupported; no false success.
2. Before a live trial, independently check exact installed binary, resources, updater and monitor locks/slot, production Xray process identity and immutable config baseline, and availability of passive packet/socket attribution tools or an isolated namespace. Do not disable kill switch or touch existing rules/routes. Read-only inspection only, separate approval for exact commands. Resource threshold of 80 MiB is preliminary, not proof of capacity.
3. Prefer independent disposable network namespace/controlled egress if supported; require explicit approval for temporary network resources. If device cannot provide suitable isolation or independent evidence, do not claim no-leak or start an uncontained provider trial. No production firewall modifications. Local-only synthetic native handshake may be the next alternative; no install of unreviewed binaries.
4. Sequential native provider trials (one at a time), private ephemeral config, loopback-only SOCKS, blackhole default, only intended outbound, no direct fallback, TLS verified and known options only. Bounded timeout and memory guard, unique child PID/start ticks and listener identity, verify owned UDP socket and header-only packet witness to endpoint; verify controlled probe client cannot make direct external HTTP requests (namespace/egress witness). Endpoint is not exit. Check 204, 401, two public exit-IP observations, matching geo, timings and RU/BY policy. Fail closed if witness missing, stale, mismatch, interruption or low resources. Negative auth/TLS and no-direct-fallback proof require explicit separately reviewed lab/physical plan; avoid unnecessary auth failures against provider.
5. Cleanup only owned test child and private temp artifacts, confirm no leftover PID/listener/socket or test config, compare production process and files, verify current pool and fresh RC2. If independent production updater changed baseline, report ambiguity, do not revert its config. No change to HA or active VPN pool. Actual physical tunnel, no-leak and cleanup rollback remain untested. Production monitoring installation requires separate acceptance/approval.
