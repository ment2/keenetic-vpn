# RC33 verified MIPS49 AF_PACKET dynamic UDP first cutover, silent-flow HARD NO-GO

**Date:** 2026-10-31. **Repository:** `ment2/keenetic-vpn`. **Only branch:** `feature/xray-v30-stable-tcp-ingress-lab-20261031`.
**Main goal ONLY:** seamless refresh of the VPN server pool. This stage tests first ownership transfer from API-less legacy Xray to API-enabled candidate with **old TCP and UDP retained**, new traffic switched and rollback.

## Verified real GitHub Actions evidence

**[RC33 41240338587](https://github.com/ment2/keenetic-vpn/actions/runs/41240338587) SUCCESS**, source commit `b278132be31b67b7600e88ea8d1f51696466421b`. Real full-system QEMU MIPS32LE Linux4.9 with pinned `xt_TPROXY` modules, official SHA256-pinned Xray 26.2.6, independent backend netns `10.77.0.3:19301` and `SLIRP restrict=on`. Two processes: legacy Xray TPROXY `12345` without API and API-configured candidate TPROXY `22345` and loopback API listener `21808`. They retain PID/start-ticks across cutover and rollback; guest checks a **synthetic** boot ID / generation journal snapshot (generation 1 at capture, 2 at cutover and 3 after rollback). This is not fsync-backed production CAS.

Unlike RC30, **old UDP source ports were not configured as constants**. The host created two active UDP sockets using OS-chosen ephemeral ports **38107 and 35206**; the guest's own statically cross-compiled MIPS32LE AF_PACKET/SOCK_RAW observer bound to `eth1` discovered their actual incoming IPv4/UDP source/destination addresses, source/destination ports and ingress interface before the cutover. The observer rejected duplicates, nonmatching destinations, bad ports and an incomplete bounded inventory. It recorded the guest boot ID + generation, flushed/fsynced the lab file, and generated exact source/destination/port `xt_TPROXY` old-flow rules **above** the broad candidate UDP rule. All five migration-rule packet counters had to be positive; normal TCP SYN was new-only directed to candidate. No synthetic outbound destination rewriting.

Real logged host witnesses:
```
RC33_HOST: RUNTIME_DISCOVERED_EPHEMERAL_UDP_SOURCE_PORTS (38107, 35206)
RC33_HOST: TCP_EXACT OLD_BEFORE 19
RC33_HOST: UDP_EXACT OLD_A_BEFORE 21
RC33_HOST: UDP_EXACT OLD_B_BEFORE 21
RC33_GUEST_DYNAMIC_UDP_FLOW_MAP_DISCOVERED_AND_PINNED count=2
RC33_HOST: TCP_EXACT OLD_DURING 19
RC33_HOST: UDP_EXACT OLD_A_DURING 21
RC33_HOST: UDP_EXACT OLD_B_DURING 21
RC33_HOST: TCP_EXACT NEW_DURING 19
RC33_HOST: UDP_EXACT NEW_DURING 19
RC33_HOST: TCP_EXACT OLD_AFTER_ROLLBACK 27
RC33_HOST: UDP_EXACT OLD_A_AFTER_ROLLBACK 29
RC33_HOST: UDP_EXACT OLD_B_AFTER_ROLLBACK 29
RC33_HOST: TCP_EXACT NEW_AFTER_ROLLBACK 27
RC33_HOST: UDP_EXACT NEW_AFTER_ROLLBACK 27
RC33_HOST: PASS_TWO_RUNTIME_DISCOVERED_UDP_FLOWS_AND_TCP_CUTOVER_ROLLBACK
RC33_GUEST_TWO_XRAY_PID_STARTTICKS_UNCHANGED_GENERATION_CAS_SYNTHETIC
RC33_PASS_DYNAMIC_DISCOVERED_UDP_TWO_FLOWS_TPROXY_CUTOVER_ONLY
RC33_HARD_NO_GO_DYNAMIC_UDP_5TUPLE_CAS_PRIVILEGED_LEGACY_FENCING_PHYSICAL
```

**[Latest full offline 41240468861](https://github.com/ment2/keenetic-vpn/actions/runs/41240468861) SUCCESS, 685/685**, source `842d0e8c3b57a53b518941986a25f73921755645`. Six RC33 static packet contracts and six RC33 release-gate mutants check original source/destination/ports/protocol/interface, duplicate identities, wrong generation, stale boot ID, missing kernel owner counter, unchanged PID/start-ticks, rollback and **an extra preexisting but silent UDP socket**. Even an all-synthetic-true physical evidence flag is bounded to `OFFLINE_KNOWN_FLOW_REVIEW_ONLY` and `production_authorized=False`. **[RC33 run 41240446070](https://github.com/ment2/keenetic-vpn/actions/runs/41240446070) SUCCESS** verified the packet harness after the independent release-gate source was added; the full 685-test run follows.

**[RC31 seven legacy SHA/policy CI 41239253164](https://github.com/ment2/keenetic-vpn/actions/runs/41239253164) SUCCESS 7/7** remains a read-only source gate, not live kernel/root enforcement.

## What is NOT proved: exact HARD NO-GO

1. **A passive packet observer cannot discover a dormant old UDP association that sent no packets during its observation window.** One independent negative mutant introduces a third old UDP socket that sends nothing: it is absent from the learned table and causes `SILENT_OR_UNOBSERVED_OLD_UDP_ASSOCIATION`. RC33 positively proves **only two traffic-active old flows**, not *all* preexisting UDP associations. It cannot guarantee a race-free flow snapshot while new packets are still arriving, or atomic cross-process ownership for every 5-tuple during a crash/rebind. A real authoritative pre-cutover session/conntrack/Xray UDP table with explicit generation fence and kernel-route/owner commit acknowledgement is still required. No claim of general no-loss seamless UDP migration is allowed.
2. **Privileged noncooperating legacy actor fencing is not proved on physical Keenetic:** S97xray contains `killall xray`; S98xray-wifi can restore conflicting TPROXY rules; S99xray-watchdog and `xray-watchdog.sh` can restart S97; cron updaters can stop/start old service; seven versioned actor SHA files do not attest live root processes or their descendants. Known RC11 root escape from cgroup-v1 remains a counterexample to software-only cgroup fencing. No live boot ID / PID/start-ticks / exec-image SHA / socket-inode descendant enumeration, universally shared lock, durable CAS journal, mandatory kernel-enforced root action fence or verified cold-boot recovery.
3. **Physical validation impossible from disposable CI:** vendor KN-1810 `4.9-ndm-5` not substituted by the Debian Malta 4.9 full-system kernel, no exact live firewall/TPROXY capability proof, USB-independent rescue and power-loss restoration of the original files not completed. Real VLESS/REALITY eligibility, DNS/IPv6 no-leak and automatic real VPN pool selection still unproven. Full hardware cutover prohibited.

**Decision:** `RC33_DISPOSABLE_ACTIVE_UDP_RUNTIME_DISCOVERY_AND_DUAL_XRAY_TPROXY_CUTOVER_ROLLBACK_SUCCESS`; `HARD_NO_GO_ALL_UDP_INCLUDING_SILENT_AND_ROOT_FENCING`; **`HARD_NO_GO_PRODUCTION`**.

**Operations:** no Keenetic jobs, no production/main/snapshot/Cloudflare, no real router firewall/routes/cron, no merge/deploy/live trial, no restrictions relaxed. All netns routing/iptables changes lived only inside disposable CI. This report does not authorize anything on the router.

**Next step on the same main goal only:** independently source the complete existing UDP association inventory (including silent flows), prove lossless freeze + generation CAS and kernel ownership fence in an isolated environment, and prove noncooperative privileged legacy root descendancy cannot restart Xray. If these prerequisites cannot be established, maintain HARD NO-GO.
