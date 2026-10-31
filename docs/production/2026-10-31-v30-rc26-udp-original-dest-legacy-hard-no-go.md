# RC26 UDP host return / original destination / privileged legacy lineage acceptance: evidence checkpoint

**Date:** 2026-10-31. **Repository:** `ment2/keenetic-vpn`. **Only allowed branch:** `feature/xray-v30-stable-tcp-ingress-lab-20261031`. **Production HARD NO-GO.**

This checkpoint does **not** run another QEMU packet experiment; it separates outcomes already actually verified from the unresolved release gates. In particular, no PASS of a static reviewer is equivalent to a real TCP/UDP positive wire witness.

## Evidence verified from GitHub Actions and runner source

- [RC21 41233646934](https://github.com/ment2/keenetic-vpn/actions/runs/41233646934): real MIPS Linux 4.9, official Xray 26.2.6, real `xt_TPROXY` TCP/UDP packet ingress, exact 25-byte payloads received by the **synthetic redirected guest backend**. **No host UDP return and no original-destination outbound proof**.
- [RC22 41234391436](https://github.com/ment2/keenetic-vpn/actions/runs/41234391436): **SUCCESS** on a bounded post-Xray-death negative sentinel test. Host TCP timeout, no sentinel received, both TCP/UDP kernel rule counters increase; **not universal DNS/IPv6 no-leak**.
- [RC23 41235004868](https://github.com/ment2/keenetic-vpn/actions/runs/41235004868): **FAILURE** on the independent non-Xray, non-TPROXY positive UDP hostfwd baseline. Guest received six 25-byte UDP messages and sent six 25-byte replies, but host observed zero. Both connected and unconnected UDP client sockets timed out with QEMU SLIRP `restrict=on`. Cause of return-path failure remains unknown; **do not blame `restrict=on` without proof** and **do not turn isolation off**.
- [RC24 41235943877](https://github.com/ment2/keenetic-vpn/actions/runs/41235943877): **SUCCESS** for actual MIPS Xray API-based synthetic TCP pool refresh, old TCP continuity, dead candidate fail-closed and explicit rollback. Does not prove safe initial legacy→API ingress migration.
- [RC25 41236987449](https://github.com/ment2/keenetic-vpn/actions/runs/41236987449): **FAILURE**. Before any temporary netns NAT cutover, `conntrack -L -p tcp` reported 0 tracked flows for an established legacy SOCKS TCP connection. Runner raised `HARD_NO_GO_OLD_TCP_CONNTRACK_NOT_ESTABLISHED_BEFORE_SWITCH`, which correctly prevented cutover. Thus the old-flow continuity of this first-migration technique is NOT proven.
- Earlier [RC11 41226245794](https://github.com/ment2/keenetic-vpn/actions/runs/41226245794) documented a **real root/privileged cgroup-v1 escape** on MIPS Linux4.9. No offline S97/S98/S99/watchdog/Wi-Fi/cron lineage checker can fence a privileged legacy root script in production by itself.

## Added versioned fail-closed review

`xray/lab/rc26_udp_legacy_cutover_gate.py` and `tests/test_xray_v30_rc26_udp_legacy_cutover_gate.py` require separately: host-received exact UDP, original destination without `freedom.redirect`, distinct backend network stack, established old-connection conntrack evidence prior to any NAT cutover, old TCP continuity and rollback, post-death TCP/UDP no-direct-fallback, DNS/IPv6, real root privileged fencing, vendor kernel and independently persistent USB-free physical rescue. Each of all seven legacy entrypoints must have independent SHA matching and boot/cron/watchdog/kernel/spawner acknowledgment. Per-process PID, parent, boot UUID, start-ticks, committed generation, socket inodes and orphan drain must agree. Mutations and a fully synthetic all-true fixture can NEVER set `production_authorized`.

**New RC26 CI is not yet established until the push workflow actually completes.** Its sole purpose is an **offline release-gate regression**; it does not resolve the experimental packet or physical blockers.

## Exact disposition

**`HARD_NO_GO_PRODUCTION`**. Current plausible next disposable experiment is a truly independent UDP return path with explicit positive host reception while keeping all network isolation, followed by an original-destination Xray backend in a distinct isolated IP/network stack. Separately address the observed RC25 old-TCP conntrack absence before any new-only NAT migration claim. Do not combine these into a misleading single PASS.

**Forbidden, untouched:** Keenetic jobs, production, main, snapshot, Cloudflare, real firewall/routes/cron, merge, deploy, live trial, restriction bypass.
