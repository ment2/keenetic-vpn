# RC36: pinned Xray 26.2.6 internal UDP ownership, real MIPS reuse after conntrack expiry; HARD NO-GO

Date: **2026-11-01**. Repo `ment2/keenetic-vpn`, exclusively branch `feature/xray-v30-stable-tcp-ingress-lab-20261031`.
Objective ONLY: seamless VPN pool refresh, including first API-less legacy → API-enabled Xray ingress migration without disturbing existing TCP/UDP sessions. **No router jobs or production/main/snapshot/Cloudflare/firewall/routes/cron/merge/deploy/live trial.**

## 1. Independent upstream source verification: Xray-core v26.2.6

The source-audit CI [41243682020](https://github.com/ment2/keenetic-vpn/actions/runs/41243682020) fetched exactly pinned [upstream commit `12ee51e4bb1d02ece4ef4b7114efa2bcdc130995`](https://github.com/XTLS/Xray-core/tree/12ee51e4bb1d02ece4ef4b7114efa2bcdc130995) and verified all five **Git blob hashes** with `git hash-object` before inspecting them:

| Path | Pinned Git blob SHA-1 |
|---|---|
| `app/proxyman/inbound/worker.go` | `ef454d21195e2df878cd129f907dfaa65f7cdff0` |
| `app/proxyman/command/command.proto` | `71f8f0dcf0e9ae83204550aa9e02eba8384cb6b0` |
| `app/stats/command/command.proto` | `9c3f9131d087a6cd5c831a5ff708d93351b865f2` |
| `app/router/command/command.proto` | `22ae95b9844039f7460d1a5db5bfc54aa251487e` |
| `proxy/dokodemo/dokodemo.go` | `e56363db0a8dd0b059b0bf705067d6c65ed0b6aa` |

At this exact version:
- The actual long-lived UDP session table is `udpWorker.activeConn map[connID]*udpConn`, with key `src net.Destination` plus `dest net.Destination` **when not in cone mode**. `getConnection` reuses the existing map object until it is closed/inactive; new entries spawn a new `proxy.Process` goroutine.
- `udpConn.lastActivityTime` is updated by reads/writes and the worker's cleanup removes entries older than `2*60` seconds in a task scheduled once per minute. This is **distinct from Linux nf_conntrack timeout**. Other termination conditions may apply; 120 seconds is not a universal guarantee of retention.
- Xray's configured `HandlerService` operations include inbound/outbound management, `RoutingService` manages routing/balancers and offers a stats **stream**, while `StatsService` exposes counters/user stats. Their verified gRPC service definitions **do not expose a complete enumeration / freeze / atomic handover of `udpWorker.activeConn`**.
- This negative result is deliberately scoped to these three source-pinned services, NOT an unproven claim about every conceivable debug, extension, custom fork or instrumented build. In particular a `SubscribeRoutingStats` stream cannot be assumed to backfill all idle associations or provide atomic snapshot semantics.

## 2. Real Xray internal UDP session reuse after conntrack expiry

**[RC36 real MIPS Linux4.9 CI 41243682020](https://github.com/ment2/keenetic-vpn/actions/runs/41243682020): SUCCESS**, verified job `124662608659`, source SHA `4d1e5468020b56b550e734b02ad5efa9f200c7b1`.

- Disposable QEMU Malta MIPS32LE Linux4.9.228, official pinned Xray 26.2.6, original-destination TPROXY, guest-only `nf_conntrack_udp_timeout` and `nf_conntrack_udp_timeout_stream = 3s`; original UDP backend lives in separate Linux netns; SLIRP `restrict=on`; no default route / WAN and **no router configuration changes**.
- A single old client UDP socket source port **42884** sends to independent backend. Guest witnesses a real kernel conntrack record; after silence it disappears. Both old and candidate Xray retain their PID/start-ticks.
- Guest independently derives the client source port from the conntrack record, checks the exact **Xray legacy debug log** `processing connection from: 10.77.0.1:<port>` occurs **once**. After the *same original client socket* sends again, bytes echo through old Xray; the count of the actual `dokodemo.Process` creation log **remains one**.
- The pinned worker source `getConnection` returns the existing `activeConn` entry without starting a second `proxy.Process`; therefore this is a strong scoped **real process-log + packet + pinned-code witness** of reuse across kernel conntrack expiry. It is not an externally exported internal-map snapshot or a 120-second retention test.
- **No migration rules were installed**: only the two original legacy TPROXY rules exist. The test correctly refuses owner transfer since full internal inventory and atomic frozen ingress are absent.

Actual CI markers:
```
RC36_SOURCE_PINNED_XRAY_26_2_6_UDP_ACTIVE_CONN_PRIVATE_MAP_CONFIRMED
RC36_SOURCE_GRPC_NO_COMPLETE_UDP_SESSION_OWNER_SNAPSHOT_IN_THREE_SERVICES
RC36_SOURCE_INTERNAL_UDP_120S_INACTIVITY_INDEPENDENT_OF_KERNEL_CONNTRACK
RC36_GUEST_FIRST_XRAY_UDP_WORKER_PROCESS_ONCE sourceport=42884
RC36_GUEST_KERNEL_OLD_UDP_CONNTRACK_EXPIRED_WHILE_BOTH_XRAY_PIDS_UNCHANGED
RC36_HOST: UDP_EXACT OLD_AFTER_EXPIRY_NO_CUTOVER 36
RC36_GUEST_XRAY_INTERNAL_PROCESS_ONCE_BEFORE_AFTER_CONNTRACK_EXPIRY
RC36_PASS_REAL_MIPS49_XRAY_UDP_WORKER_REUSED_ACROSS_CONNTRACK_EXPIRY_NO_CUTOVER
RC36_HARD_NO_GO_NO_COMPLETE_XRAY_UDP_OWNER_OR_ATOMIC_FREEZE
```

## 3. Root/legacy restart fencing negative witness

**[RC36 offline 41243746771](https://github.com/ment2/keenetic-vpn/actions/runs/41243746771): SUCCESS 724/724**. The new test launches a **disposable unprivileged** independent subprocess that writes into a sandbox event file **while controller holds an exclusive `flock`**. A cooperating second `flock` attempt correctly fails, but the noncooperating actor completes its write. This is evidence **advisory flock does not enforce mandatory containment** even before adding root privileges. No live S97/S98/S99/watchdog/cron was executed.

The existing seven versioned root entrypoint snapshot gates, negative mutation witnesses, generation CAS/PID/start-ticks/cgroup-v1 escape gate and hardware rescue gates were rerun within the 724 tests. A PASS means dangerous cases were **rejected**, not that real root descendants are fenced on Keenetic.

## 4. Exact remaining blockers to full seamless VPN-pool implementation

1. **Missing Xray session inventory API:** internal `udpWorker.activeConn` exists, and the experiment showed a session can outlive its conntrack entry. But stock Xray 26.2.6 exposes no verified complete, stable `connID`+owner-process+socket-cookie inventory in the three configured services. The old production Xray is API-less, making the first-migration problem even harder. A private map cannot safely be inferred from `/proc/net/udp`, conntrack, logged activity or routing-event streams. No instrumented replacement and no agreed live migration mechanism has been proven.
2. **Missing race-free kernel freeze/commit:** current `xt_TPROXY` cutover rules are not an atomic, complete lock across all idle/new UDP 5-tuples, packet arrival, process failure, boot ID and durable generation CAS. Existing models validate negative predicates but **do not** perform real kernel-enforced freeze or crash-atomic rollback. Unknown association routing must fail closed instead of silently switching the owner.
3. **Mandatory legacy root fencing absent:** S97 `killall xray`, S98 packet rules rewrite, S99/watchdog/cron starts/stops and root descendants remain beyond a voluntary `flock`. Prior cgroup-v1 root escape is an explicit counterexample. No physical mandatory kernel-enforced root fence, live descendant executable SHA/PID/start-ticks/socket-inode scan, hardware USB-free rescue/power-loss acceptance or vendor `4.9-ndm-5` acceptance has passed.
4. **No production-level end-to-end:** real VLESS/REALITY pool authorization, DNS/IPv6 no-leak and continuous UDP across arbitrary pool refresh are still unproved.

**Decision: `RC36_PINNED_XRAY_UDP_ACTIVE_CONN_REUSE_MIPS49_SUCCESS`; `RC36_ROOT_ADVISORY_FLOCK_BYPASS_NEGATIVE_SUCCESS`; `HARD_NO_GO_PRODUCTION`.**

The next work must remain only on seamless pool updates: either produce a fully testable independent Xray UDP session-owner snapshot with kernel freeze and mandatory boot-time privileged fencing under disposable CI and later separate physical authorization, or explicitly retain the blocker. **Do not make a fork, fake session API, bypass restrictions, or treat a synthetic CAS result as kernel/hardware proof.**
