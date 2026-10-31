# RC32 — first dual-Xray MIPS49 TPROXY cutover: pinned old TCP/UDP flows PASS; generic migration HARD NO-GO

**Date:** 2026-10-31. **Repository:** `ment2/keenetic-vpn`. **Only branch:** `feature/xray-v30-stable-tcp-ingress-lab-20261031`.
**User objective:** seamless VPN pool updates, including one-time migration of legacy Xray SOCKS/TPROXY listeners to API-enabled candidate **without losing active TCP/UDP and without direct fallback**.

This readback **supersedes the older pre-fix first-cutover conclusion** in `docs/production/2026-10-31-v30-rc31-first-tproxy-fencing-and-rescue-hard-no-go.md`. RC31's privileged-hardware HARD NO-GO itself remains correct; its statement that no TPROXY first-cutover or rollback witness existed became obsolete after CI 41239200367.

## 1. Exactly what the real full-system packet experiment proved

**[RC30 full MIPS32LE Linux 4.9 CI 41239200367](https://github.com/ment2/keenetic-vpn/actions/runs/41239200367) SUCCESS**, source SHA `65a491e26a53ff1a5912890b523a7776065f4b1d`, job `124649328223`:
- Disposable `qemu-system-mipsel -M malta`, Debian `4.9.0-13-4kc-malta`, verified 4.9 `xt_TPROXY` modules and pinned official Xray 26.2.6 MIPS32LE. Independent Linux backend netns binds original `10.77.0.3:19301` reachable only by TAP; `SLIRP restrict=on` remains; no WAN/default-route or production router changes.
- **Legacy Xray (no API)** retained transparent ingress TCP+UDP `12345`. Separate **API-configured candidate** listened on TPROXY TCP+UDP `22345` and loopback API `21808`, started under UID 65534 / only CAP_NET_RAW / no_new_privs. Exact candidate API config and listener were asserted. This particular test **did not execute a gRPC API pool change**; RC24 separately proved real MIPS32LE API pool BO/ADO, failed candidate, old TCP preservation, explicit rollback and same PID/ticks.
- Both Xray processes kept their PID/start-ticks during the test. Guest synthetic in-memory generation 2 at cutover and 3 at rollback; **not a durable CAS journal or an actual privileged watchdog fence**.
- Before cutover host bound old TCP source port 21111 and old UDP socket port 21112. Host TCP and UDP exchanged exactly matching bytes with the independent backend.
- During cutover guest installed exact old source-tuple pins **above** the broad candidate UDP rule, and a TCP SYN candidate rule; real mangle PREROUTING TPROXY counter assertions required all 4 migration rule owners to register packets. Old TCP socket remained open and exchanged matching bytes; **the same old UDP socket** received matching bytes. New TCP and UDP source ports received exact matching backend echoes. All packets retained their original destination to the separate backend (no Freedom redirect).
- Rollback removed exactly four disposable migration rules, verified only the two original legacy TPROXY rules remained, and verified the same old TCP/UDP sockets kept working as well as newly opened post-rollback TCP/UDP streams.

GitHub log markers:
```
RC30_HOST: TCP_EXACT OLD_BEFORE 19
RC30_HOST: UDP_EXACT OLD_BEFORE 19
RC30_GUEST_NEW_ONLY_TUPLE_PINNED_CUTOVER_READY
RC30_HOST: TCP_EXACT OLD_DURING 19
RC30_HOST: UDP_EXACT OLD_DURING 19
RC30_HOST: TCP_EXACT NEW_DURING 19
RC30_HOST: UDP_EXACT NEW_DURING 19
RC30_GUEST_CUTOVER_RULES_REMOVED_ROLLBACK_READY
RC30_HOST: TCP_EXACT OLD_AFTER_ROLLBACK 27
RC30_HOST: UDP_EXACT OLD_AFTER_ROLLBACK 27
RC30_HOST: TCP_EXACT NEW_AFTER_ROLLBACK 27
RC30_HOST: UDP_EXACT NEW_AFTER_ROLLBACK 27
RC30_HOST: PASS_KNOWN_OLD_TUPLE_TCP_UDP_ACROSS_CUTOVER_AND_ROLLBACK
RC30_GUEST_TWO_XRAY_PID_STARTTICKS_UNCHANGED_GENERATION_CAS_SYNTHETIC
RC30_PASS_KNOWN_TUPLE_TPROXY_TCP_UDP_INITIAL_CUTOVER_ONLY
RC30_HARD_NO_GO_DYNAMIC_UDP_5TUPLE_CAS_PRIVILEGED_LEGACY_FENCING_PHYSICAL
```
This is **actual isolated first TPROXY packet ingress cutover for two known old source tuples**, NOT a claim of arbitrary live VPN session preservation. The test explicitly pins a known source address+port+protocol with fixed destination port and interface; it has NOT implemented an authenticated, automatic, complete 5-tuple snapshot that captures and fences **all** preexisting UDP associations.

## 2. Rejected false positives are preserved, not erased

[RC30 CI 41238983743](https://github.com/ment2/keenetic-vpn/actions/runs/41238983743) FAILURE exposed an important true misrouting condition: generic candidate UDP rule was inserted before the pinned legacy UDP rule. Counters (in [failure artifact](https://github.com/ment2/keenetic-vpn/actions/runs/41238983743)) showed **0 packets** in old UDP pin and **2** on candidate general UDP rule despite a working old UDP echo. This was silently stealing old UDP association, so the guard correctly failed before rollback. Source was fixed by changing `iptables -I` insertion ordering and requiring positive counters on all four split rules. Intermediate CI failures from source test path, absent `iptable_filter` in guest, and readiness/rule witness are **not** packet-path successes.

- [RC30 offline 41239200396](https://github.com/ment2/keenetic-vpn/actions/runs/41239200396) **SUCCESS 666/666**.
- [RC31 seven versioned legacy snapshot SHA256 evidence CI 41239253164](https://github.com/ment2/keenetic-vpn/actions/runs/41239253164) **SUCCESS 7/7**. It asserts failure/NO-GO on missing/hashes drift/PID reuse/orphans/root descendants and explicitly does **not** claim any physical root actor is fenced.
- [Full offline 41239253080](https://github.com/ment2/keenetic-vpn/actions/runs/41239253080) **SUCCESS 673/673** at commit `9daad1fa8c4dd32b08a9486071f8474c1adebf45`.
- [RC29 original destination independently routed 41238192710](https://github.com/ment2/keenetic-vpn/actions/runs/41238192710) and [RC30 separate post-Xray-death negative witness 41238549653](https://github.com/ment2/keenetic-vpn/actions/runs/41238549653) are prior distinct SUCCESS, **not** proof of universal no-leak after the dual-process first cutover.

## 3. Concrete HARD NO-GO for generic seamless VPN pool release

1. **Automatic arbitrary UDP association ownership is NOT solved.** TCP new flows have SYN; UDP does not. A finite manually pinned source tuple for one test cannot identify and freeze every existing UDP association, protect ambiguous NAT/rebind cases, or atomically move unknown/new UDP without a verified kernel flow map and crash-safe generation ownership. No positive universally dynamic 5-tuple cutover under the vendor MIPS kernel. Do not generalize this fixture to production.
2. **Privileged legacy first-boot / watchdog / cron actors are NOT fenced.** Read-only source evidence includes S97 `killall xray`, S98 repeatedly repairing WiFi TPROXY routes, S99 PID-only watchdog launcher, watchdog restart of S97, and cron updater invoking service stop/start. A cooperative flock is not used by all privileged legacy executors; `killall` can kill both Xray owners mid-session. Earlier root cgroup-v1 escape is a real counterexample. Versioned source SHA snapshots are not live-process SHA/readback, and PID/start-ticks alone cannot fence orphaned root descendants.
3. **Real router operational gates NOT met:** no durable generation CAS / single authoritative ingress owner / rollback journal; no physical KN-1810 vendor `4.9-ndm-5` kernel/iptables verification, no real VLESS/REALITY VPN or DNS/IPv6 no-leak cutover proof, no USB-independent rescue/power-loss recovery, and no separate owner authorization for live changes.

### Decision

**`RC30_DISPOSABLE_KNOWN_TCP_UDP_TPROXY_FIRST_CUTOVER_AND_ROLLBACK_SUCCESS`**.

**`HARD_NO_GO_GENERIC_DYNAMIC_UDP_5TUPLE_AND_PRIVILEGED_LEGACY_FENCING`**.

**`HARD_NO_GO_PRODUCTION`**. No Keenetic jobs, no production/main/snapshot/Cloudflare/physical firewall/routes/cron, merge/deploy/live trial. This is a bounded research result only.

**Only next task related to main goal:** implement and prove a dynamic full-flow classifier with source/destination/protocol/interface/boot+generation CAS and exact per-flow old/new Xray ownership on disposable MIPS49, plus independently enforced privileged legacy descendant fencing or retain NO-GO. No return to unrelated SLIRP hostfwd research.
