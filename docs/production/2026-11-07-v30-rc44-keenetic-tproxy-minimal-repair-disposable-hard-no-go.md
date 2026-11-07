# RC44: practical first-migration TPROXY repair and rollback, disposable CI only

Date: 2026-11-07. Repository ment2/keenetic-vpn. Only branch feature/xray-v30-stable-tcp-ingress-lab-20261031. **LAB SUCCESS; REAL KEENETIC REPAIR AND FIRST API CUTOVER NO-GO**. User permits service interruption and existing TCP/UDP session loss during first migration. This does not waive independent rollback and fail-closed requirements.

## Actual RC43 snapshot and exact source-level cause

On November 7 the live read-only Keenetic inspection observed Xray PID 815 / start_ticks 4570, boot ID 17cc872c-36cb-4411-899e-9eec5f3155c9; unique SOCKS TCP 10808 and TPROXY TCP/UDP 12345 listener ownership. It observed two PREROUTING -> XRAY_WIFI entries, yet no TPROXY target inside XRAY_WIFI. IPv4/IPv6 FORWARD DROP and XRAY_KS_HOME existed, with two duplicated FORWARD jumps. Existing 15-second canary matched SHA256 8e57ef5054f53174a35d906d34eab073dd6d787607cb02f29d83364ae3abc203. Its single fresh read-only --plan failed at the process/socket-exclusive gate; a separate later process snapshot found only the stable PID 815. No physical change occurred.

RC44 reconstructed the exact nine original destination RETURN lines from the versioned xray-wifi-rules.sh source, SHA256 ead5de5555aaab1170a140ca3d41ea546330a99ba873b1961bee536bc12780ef. The reconstructed chain SHA256 was 44f3d783cae72cb3987133c3f84abac389f1f1e4d91b98bafeafd04f1a5c3891, **an exact match to the live RC43 read-back**, not an approximation.

The original script first flushes XRAY_WIFI, appends nine RETURN exceptions, tries to append TCP and UDP TPROXY rules, then checks/creates PREROUTING jumps. It has NO checked exit at TPROXY append and no set -e. Thus when kernel rejects both TPROXY appends and existing PREROUTING checks succeed, shell reports success while leaving only nine RETURN rules. RC44 executed the original SHA-verified shell source in a disposable fake-iptables sandbox, injected exactly those two failures and witnessed exit 0, nine RETURN and zero TPROXY. This identifies a **real error-handling defect in versioned source**, but NOT which physical errno or interrupted process caused the actual router state. Do not claim live kernel module incompatibility without separate evidence.

## Minimal repair proposal, NOT authorized for physical execution

Preconditions: fresh full rule snapshot and hash, exact nine RETURN chain unchanged since RC43, current binary/backend supports TPROXY and no simultaneous root writers, real listener and policy marks verified, fail-closed and separate off-USB restore proven, local operator access, separately approved exact operation and rollback.

Proposed two-rule append transaction is ONLY for review; a disposable Ubuntu runner used iptables-restore --noflush:

    *mangle
    -A XRAY_WIFI -p tcp -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000
    -A XRAY_WIFI -p udp -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000
    COMMIT

Do not flush XRAY_WIFI, edit PREROUTING, replace all mangle tables or modify FORWARD, the kill-switch, cron, Xray config, WAN routes or S97 to carry out this minimal repair. If any precondition drifts, abort before writing. Verify native rule order: original nine RETURN then exact TCP and UDP TPROXY, unchanged two scoped PREROUTING jumps, fwmark 0x40000000 / table100 local lo, Linux socket owner and actual **Wi-Fi TCP and UDP** packets through Xray, OpenAI via VPN, DNS/IPv6 no-leak and fail-closed. Simple bound socket or positive counter alone is not an acceptance test.

Proposed inverse selectors, not physically approved: remove only the transaction-owned UDP TPROXY and TCP TPROXY entries, using the exact same protocol/port/mark. On any error restore original saved rule semantics and verify policy state, or remain fail-closed and use independent recovery. Two separate rule deletions are NOT claimed as one atomic rollback on physical hardware. Ensure a mandatory, reviewed maintenance quiescence procedure prevents S98, watchdog, cron and already-running children from changing the table during repair.

## Genuine disposable packet and rollback results

[RC44 real packet CI 42347863653](https://github.com/ment2/keenetic-vpn/actions/runs/42347863653) **SUCCESS 19/19 focused tests**, code commit 031530f5c1fbd0a5f146868ef54547d5ce4ce05a. Earlier [RC44 42347756659](https://github.com/ment2/keenetic-vpn/actions/runs/42347756659) **SUCCESS 11/11 focused** before source race additions. Full offline CI [42347863507](https://github.com/ment2/keenetic-vpn/actions/runs/42347863507) **SUCCESS 845/845**.

The real native Ubuntu kernel CI used only two freshly created isolated network namespaces, one veth, a synthetic original destination 198.18.44.10 and a Python IP_TRANSPARENT TCP/UDP sink (NOT a live or patched Xray). No default routes; ip_forward=0; IPv4 AND IPv6 FORWARD DROP. Before repair, both protocols failed closed and the sink saw nothing. A single iptables-restore --noflush append created the two targeted TPROXY rules; exact TCP and UDP payloads were then observed by genuine transparent sockets, with matching counter witnesses. TCP returned an exact echo. Kernel counters were TCP protocol 6: 5 packets / 283 bytes; UDP protocol 17: 1 packet / 43 bytes. The inverse deleted exactly the two TPROXY selectors. With only volatile iptables-save timestamps and built-in counters normalized, original kernel mangle rule semantics and **order** matched; fresh TCP and UDP were again blocked. Fail-closed checks remained true. These are disposable runner Linux facts, NOT vendor MIPS Linux4.9 physical acceptance or a full Xray application-path test.

## Three source-confirmed supervisor / cron race mechanisms

1. S98xray-wifi checks the TPROXY chain and retries the non-atomic flush-and-rebuild xray-wifi-rules.sh every **60 seconds** when absent, without an enforced migration lock. Even a successful two-rule append can be overwritten by S98 if its own next TPROXY append fails. A synthetic negative fixture demonstrated an eleven-rule repaired chain becoming nine rules after a competing failed rebuild. Existing S98 parent PID does not prove privileged descendant absence.
2. xray-ks-home-watch.sh invokes xray-ks-home.sh every **15 seconds**. The latter inspects only the FIRST FORWARD jump (sed -n 2p) and inserts a new XRAY_KS_HOME jump if the first is different, without checking for an existing one elsewhere. A deterministic source model produces a duplicate. The two physical duplicate FORWARD jumps were observed, but their historic exact origin has NOT been traced; do not casually delete kill-switch protections.
3. The hourly updater is **STAGED_ONLY** and does not auto-promote the pool, but uses the real Xray binary with run -test -config for candidate validation. This can temporarily produce a second Xray executable PID when canary --plan tries to prove exclusive process ownership, consistent with the single RC43 failure and later unique Xray PID 815. This is a plausible race, **not proven incident attribution**. The separate cron guard has an enabled-flag recovery path. Watchdog/S97 can globally killall Xray. Root descendants are not independently fenced.

Files: xray/lab/rc44_tproxy_repair_gate.py, rc44_wifi_rules_failure_injection.py, rc44_tproxy_repair_netns.sh, rc44_tproxy_packet_witness.py, rc44_tproxy_repair_runner.sh, rc44_legacy_race_review.py, tests/test_xray_v30_rc44_*.py, and .github/workflows/xray-v30-rc44-tproxy-repair.yml. The 845-test offline CI covers narrow source and mutation checks, not any new hardware change.

## Exact next GO/NO-GO sequence

1. Fresh read-only inspection of original Keenetic xt_TPROXY support/iptables-restore backend and previous S98 repair errors, currently present nine rules plus original PREROUTING target, cron and S98 child activity, independent fail-closed and process owner. No speculative module load or write on the router.
2. Establish independent off-USB authenticated encrypted recovery and verify original file permissions and at least a disposable restore. Existing verified 11/11 router archive lives on the same USB, while HA TCP22 reachability alone proves no remote backup or restore.
3. Prepare and review exact maintenance quiesce and rollback for S98, S97, S99, watchdog, cron/children and kill-switch repair. No advisory-lock-only assurances; RC42 root lab showed a real counterexample. Retain an independent local access path.
4. **Ask approval of the complete exact physical change only after prior evidence**, then perform narrowly scoped restoration and actual TCP/UDP acceptance, with immediate rollback when failed.
5. After the current old Xray ingress is stable and a fresh --plan actually passes, separately authorize the reversible 15-second API-enabled Xray first-migration canary (which ALWAYS reverts), then a different permanent promotion. Service interruption is allowed but physical failure must remain recoverable.

**Decision: RC44 DISPOSABLE CI PASS; PHYSICAL FIREWALL REPAIR HOLD; FIRST API MIGRATION NO-GO until real preflight, safe quiesce, and reviewed exact rollback.** No Keenetic jobs, router write, real firewall/routes/cron, Xray signals, Cloudflare, production/main/snapshot, merge, deploy or live trial were performed.
