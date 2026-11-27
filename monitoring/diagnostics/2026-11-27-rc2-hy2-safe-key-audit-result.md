# RC2 Hysteria2 — safe key audit and physical isolation gate

Date: 2026-11-27. Branch feature/rc2-hysteria2-monitor-candidate-20261127. Baseline report c9b40123ce91e4fef8edae460747e630151795a6. No production modification, no physical tunnel launched.

## Authorized diagnostic
Approved exact command from b6433c90635bafcaf88d98fa3ed41fe1c696b6e6, SHA256 9f1ee657799ba147c138d20b06600d36a555abaed6a2ce38b1b19db13a54f687, blob fd4da9fc746b49e0924d3e699ce1dacd5f1e79b9, 4095 bytes including LF. SHA256 verified locally and Git blob/length matched. Submitted once; Keenetic Mobile job 3ea7df84-d0f8-4897-ab9e-6b91e135a321, created 20:03:45.032Z, DONE exit 0. No repeated submission.

```
RECORDS 12 HYSTERIA2 2
HY 1 EXTRA_NAMES [] MASKED_COUNT 1 DUPLICATE False
HY 2 EXTRA_NAMES [] MASKED_COUNT 1 DUPLICATE False
UNCHANGED True
```

The safe-name filter did not reveal the unknown key on either record. It does not establish that the keys are identical, that they are secrets, or that they are security flags. Root cause of the unknown option is still unconfirmed. Previous actual installed Xray config-test passed Hysteria2+Salamander (synthetic configuration), not live tunnel. ECH lowercase query key was absent in previous audit. No credentials disclosed. UNCHANGED covers the checked paths; not a comprehensive integrity attestation.

## Candidate update and regression
Code commit eaa740cdd754c1980b38a0a4afff69c20519bae2. Recognizes normalized TLS-verification aliases for rejection/classification only (including allowInsecure, skipCertVerify, noverify, case and separator variants). All unreviewed aliases remain rejected even with a false-looking value; never silently drop, enable insecure TLS, or admit. Canonical insecure=0 behavior unchanged. The actual provider option has not been mapped. Sources of alias conventions: https://github.com/Leadaxe/singbox-launcher/blob/main/contract/docs/generated/protocols/hysteria2.md and https://github.com/shelad3/ncx-tunnel/blob/main/docs/PROTOCOLS.md . These describe client conventions, not this provider's contract.

Local 56 tests, 55 passed and one repository-dependent check skipped; full CI 46061284654 SUCCESS, 56/56 candidate + 276/276 baseline tests, all four jobs passed. Unit job 140715892765; real isolated Mosquitto job 140715892991 (12 nodes, 110 publications, 97 retained discovery, 13 nonretained states); QUIC AMD64 140715893021 and MIPS32LE QEMU-user 140715893071 (plain and Salamander positive, wrong auth and TLS name no HTTP witness). Synthetic endpoints, not provider live checks.

## Next command (prepared only, separate owner approval required)
monitoring/lab/mixed_rc2/device-classify-isolation-command.txt, 4048 bytes incl LF, SHA256 0476f4ebb74f9ac7dd2689289df5e3e3fee138c63da7d308ed094cc21e0ec511, blob ef99b8016dac25c12c6e756e0f1d114cef03e15b. Uses reviewed source pins, one existing audited subscription reader invocation, updater-idle witness, unchanged-files check. Emits only bounded public option categories, known TLS flag truth categories (not raw values), identifier/ASCII flags and equality of extra key sets. No raw unknown key, raw subscription, UUID, auth or obfs password. Checks executable presence (ip, unshare, nsenter, tcpdump, ss, strace), proc namespace/UDP visibility, and selected kernel config flags if available. Does not create namespaces or run packet capture. Syntax and six synthetic classification/no-raw-secret fixtures passed. Presence of tools/flags is not operational proof. If still UNCLASSIFIED, obtain sanitized provider documentation or user-supplied public parameter name, rather than keep guessing or weaken redaction.

## Physical test acceptance gate — HARD NO-GO
1. Classify the actual option and verify semantics against provider/client documentation. If it cannot be mapped without reducing TLS security, keep both Hysteria2 records visible as unsupported. No false success and no production switch.
2. Verify isolation capabilities with separately approved exact read-only/temporary diagnostic, independent packet/socket attribution, available memory >=80 MiB (preliminary guard), stable installed Xray SHA, updater/monitor idle, production process identity and config baseline. Tool presence alone is insufficient. No production firewall/routes/kill-switch changes. If kernel cannot provide an independently enforceable isolation path, stop; design alternative lab/physical plan before live trial.
3. Prepare one sequential temporary test per real Hysteria2 endpoint, exact reviewed config only, separate owner approval. Loopback-only SOCKS, blackhole default, sole selected outbound, strict TLS and no fallback. Bound child lifetime, memory and cleanup; isolate probe client's direct egress and independently attribute QUIC UDP to test process and endpoint. Require actual HTTP 204, OpenAI 401, matching independent public egress IP and country, durations and RU/BY rejection. No raw packet payloads or credentials exported. Test one at a time; stop on ambiguity, low memory or missing witness. No deliberately bad authentication against provider without separately reviewed approval.
4. Cleanup exact owned test child and private temp artifacts; verify no leftover listener or child, unchanged production process/config/kill-switch, fresh RC2 and existing pool. If concurrent normal updater changed config, report ambiguity, do not roll it back. No live HA changes. Real provider handshake, no-leak and cleanup rollback remain untested. Production monitoring installation requires separate acceptance/approval.
