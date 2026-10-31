# RC27: real first SOCKS TCP ingress handover without killing legacy Xray; TPROXY and production HARD NO-GO

**Date:** 2026-10-31. **Repository:** `ment2/keenetic-vpn`. **Only branch:** `feature/xray-v30-stable-tcp-ingress-lab-20261031`.
**Scope:** user goal **seamless VPN pool refresh**, specifically one-time migration of the occupied legacy SOCKS ingress to API-enabled Xray. No router jobs, production/main/snapshot/Cloudflare/real firewall/routes/cron edits, merge, deploy or live trial. All netfilter changes were only within a new isolated and disposable GitHub runner network namespace with no other interfaces or default route.

## Verified first migration and real CI outcome

The existing RC24 [MIPS32LE API pool update SUCCESS 41235943877](https://github.com/ment2/keenetic-vpn/actions/runs/41235943877) proved new pool refresh without process restart *after* API availability. RC25 tried first same-port legacy ingress handover using kernel conntrack NEW and obtained a **real old TCP ConnectionResetError** in [41236807375](https://github.com/ment2/keenetic-vpn/actions/runs/41236807375). Subsequent RC25 [41236987449](https://github.com/ment2/keenetic-vpn/actions/runs/41236987449) observed `0 flow entries` before switch, so it correctly hard-blocked handover.

**RC27 corrects the narrow lab strategy**: a disposable Linux `unshare --net` with native runner kernel and genuine Xray **26.2.6 MIPS32LE binary executed under qemu-mipsel** runs:
- Old Xray without API continues owning original loopback SOCKS TCP port `127.0.0.1:10808`.
- Independent API-enabled candidate Xray listens on `127.0.0.1:20808`, loopback API at `21808`; synthetic echo A and B only.
- Only initial **TCP SYN** to 127.0.0.1:10808 matches a test-only nat OUTPUT redirect. A test checks a unique exact canonical rule `-A OUTPUT -d 127.0.0.1/32 -p tcp -m tcp --dport 10808 --tcp-flags SYN,RST,ACK SYN -j REDIRECT --to-ports 20808`.
- Before and during cutover the already-open TCP client is verified by `/proc/net/tcp` TCP `ESTABLISHED` state and **same socket inode**; exact old A response bytes are checked repeatedly.
- New connections on the same client-facing SOCKS port route through the candidate B. After synthetic B backend shutdown, new requests fail rather than silently routing to A/direct, while old A TCP still exchanges bytes.
- Explicit rollback checks exclusive ownership of the canonical NAT OUTPUT rule, removes **only that one isolated rule** by index, reads back the now-empty chain and verifies new clients use old A again. Both Xray child PIDs and start_ticks identities are unchanged throughout; in-memory generation increments 1→2→3.
- A cooperating *synthetic test-only* watchdog requires the same `flock` and cannot restart the legacy process during cutover. This does **NOT** fence real privileged S97/S98/S99/watchdog/cron descendants.

Real [GitHub Actions RC27 41237894405](https://github.com/ment2/keenetic-vpn/actions/runs/41237894405) **SUCCESS** and the specific required witnesses in the job:
```
RC27: OLD_TCP_SOCKET_INODE_ESTABLISHED_BEFORE_SYN_ONLY_CUTOVER
RC27_DIAG: PRE_SWITCH_CONNTRACK_ENTRY_COUNT 0
RC27: COOPERATIVE_WATCHDOG_RESTART_SUPPRESSED_NO_KILLALL
RC27: EXACT_SYN_ONLY_NAT_RULE_CANONICAL_READBACK_CONFIRMED
RC27: OLD_TCP_SOCKET_INODE_UNCHANGED_POST_SWITCH
RC27: PASS_FIRST_INGRESS_SOCKS_NEW_ONLY_TO_API_XRAY_OLD_TCP_DRAINS
RC27: PASS_FAILED_CANDIDATE_NEW_REQUEST_BLOCKED_OLD_FLOW_LIVE
RC27: EXACT_SYN_ONLY_NAT_REMOVED_AND_READBACK_VERIFIED
RC27: PASS_ROLLBACK_SAME_10808_OLD_PROCESS_PID_STARTTICKS_AND_CAS
RC27: HARD_NO_GO_TPROXY_UDP_UNCOOPERATIVE_WATCHDOG_VENDOR_HARDWARE
```
[Offline CI 41237894447](https://github.com/ment2/keenetic-vpn/actions/runs/41237894447) **SUCCESS 640/640**. RC27 structural source suite 8/8 passed. Historical earlier iterations rejected false PASS on stale test path, noncanonical `iptables -C`, and noncanonical `iptables -D`; final run requires actual packet evidence, unique canonical readback, strict rollback verification.

## Remaining blockers directly relevant to seamless pool updating

1. **TPROXY ingress:** This is only *local SOCKS TCP* inside native runner netns. Real router `0.0.0.0:12345` TPROXY TCP/UDP PREROUTING path and existing UDP association continuity have **not** been tested across legacy→API first migration. UDP has no SYN; the tested trick cannot preserve existing UDP flows. Do not treat RC21 separate MIPS Linux4.9 UDP backend ingress experiment as a first migration test.
2. **Real network shape:** The Xray binary uses MIPS32LE under **user-mode QEMU** with the **native Ubuntu runner kernel**, not the vendor MIPS 4.9 kernel, Wi-Fi TPROXY/packet path or production conntrack/iptables variant. The RC25 zero-conntrack witness remains real and the RC27 result does not retrofit an old conntrack entry.
3. **Privileged watchdog/fencing:** Cooperative flock in the isolated lab proves no control over actual root S97/S98/S99, cron, watchdog descendants; their kernel-enforced fencing and CAS durability are unverified. A privileged cgroup-v1 escape is an existing counterexample. Arbitrarily deploying only the NAT redirect would risk forced `killall xray` mid-session.
4. **Durability / recovery:** RC27 generation is in memory. Reboot recovery, atomic persistent coordination, independent USB-free physical rescue, DNS/IPv6 no-leak and true VLESS/REALITY pool health were not proven. Even with the new local SOCKS evidence, no claim of zero packet loss on real hardware is supported.
5. **Current installed Xray has no API:** An on-router first migration still needs approved staged API-enabled candidate, safe ingress ownership transition for both protocol families, protected watchdog ownership and independently viable rollback. No approval or deployment commands are inferred here.

**Decision:**
`RC27_FIRST_SOCKS_TCP_MIGRATION_DISPOSABLE_SUCCESS`.
`RC27_TPROXY_TCP_UDP_AND_PRIVILEGED_LEGACY_HARD_NO_GO`.
`HARD_NO_GO_PRODUCTION`.

**Next work, only seamless pool:** in disposable CI prove stateful old-vs-new TPROXY TCP/UDP flow mapping, first migration rollback under original destination, and watchdog-fencing negative mutations, without weakening no-direct-fallback. On inability to establish real TPROXY old-flow preservation, document HARD NO-GO rather than fake a seamless claim.
