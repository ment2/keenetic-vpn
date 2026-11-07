# RC42: uninstrumented Xray UDP owner visibility, real kernel DROP, stale CAS and root descendant negative proof

**Date:** 2026-11-07. **Repository:** ment2/keenetic-vpn. **Only branch:** feature/xray-v30-stable-tcp-ingress-lab-20261031. **Release decision: HARD_NO_GO_PRODUCTION.**

## Baseline source authority and limits

The upstream Xray-core v26.2.6 commit is 12ee51e4bb1d02ece4ef4b7114efa2bcdc130995. Its app/proxyman/inbound/worker.go Git blob is ef454d21195e2df878cd129f907dfaa65f7cdff0, independently pinned in RC36. The worker has a private Go map named activeConn, keyed by a connID containing the source and, depending on cone mode, original destination. It is guarded by its own RWMutex and has a cleanup timeout independent of kernel conntrack. The original inbound UDP listener can carry multiple private associations through one kernel socket.

RC40, GitHub CI 42295498150 SUCCESS: two independently identified UDP sockets provided real packet evidence that the same kernel-conntrack-empty snapshot can coexist with an active private Xray UDP association (A) and no previous association (B). RC41, GitHub CI 42342992003 SUCCESS: a test-only Go file compiled inside the pinned Xray source package successfully inspected its own private map, including an idle A and newly arriving B; new packets invalidate a previously completed snapshot unless kernel ingress is actually held.

**Independent read-only inventory of the already-running uninstrumented legacy process remains unavailable through the verified interfaces.** The pinned proxyman/Stats/Routing gRPC services do not expose full private activeConn rows, active lineage, socket cookies or an atomic ingress snapshot operation. Linux procfs process descriptors and /proc/net/udp expose kernel descriptors and sockets, not all Go map rows. Another instrumented test binary does not share the existing legacy process heap or owner authority. One could investigate privileged ptrace, debugger/core snapshots, uprobes or modified instrumentation in a different authorized design; this is NOT a supported, proven, non-disruptive, race-free complete inventory path. Do not claim absolute theoretical impossibility of every future mechanism.

## RC42 real kernel packet barrier: verified disposable Linux netns

[GitHub Actions 42343962946](https://github.com/ment2/keenetic-vpn/actions/runs/42343962946) **SUCCESS, 16 dedicated contracts/mutants and real packet experiment**, source commit 2bb157ba02979bb1e167438af0ee06273490cecf.

An Ubuntu 24.04 GitHub runner created two isolated network namespaces with a dedicated veth pair, addresses 10.42.0.1 and 10.42.0.2 and no default routes. One persistent UDP client and one echo server recorded process PID/start ticks, kernel boot ID, client and server socket inode and Linux SO_COOKIE. The client used source port 51011 and cookie 2 during the first run.

- Before rules change: exact UDP echo returned 11 bytes.
- A single native nftables batch inserted an INPUT hook counter DROP for only synthetic port 19542; native counter incremented, UDP client timed out, server did not receive the packet.
- A native delete of that disposable table returned the complete ruleset to the byte-identical empty original, digest e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855.
- Same socket received 10 exact echoed bytes after restore; boot ID and PID/start ticks remained stable.
- An actual ephemeral runner journal used fcntl flock, tempfile fsync, atomic os.replace, directory fsync and CAS on boot ID, generation, process identity and rules digest. Observed generations 1 ORIGINAL -> 2 FROZEN_DROP -> 3 RESTORED. The ruleset digest during DROP was fcf2f4843c842a0383f29eec7dc634a18270aa96d41d10d94c2b138e76d11b7c. Independent tests reject stale generation/boot/rules/PID/start ticks, corrupted checksums, symlinks, two concurrent writers and a pre-replace fault.

**Interpretation:** actual nftables DROP is a packet-losing ingress barrier, not a buffered freeze. A file journal on an ephemeral runner is not a signed kernel-authoritative receipt, nor storage durability proven across power failure. No Xray TPROXY migration, old/new owner switchover or physical KN-1810 acceptance occurred.

## RC42 independent root actor vs controller advisory lock: verified real kernel counterexample

[GitHub Actions 42344147959](https://github.com/ment2/keenetic-vpn/actions/runs/42344147959) **SUCCESS, 5 dedicated source contracts and real root-process kernel experiment**, source commit 75210aa2ad707c3b809c08d490fa425d6dbdd48d.

The same test-only namespace was frozen with real nftables DROP. Controller kept an exclusive advisory flock and ephemeral journal generation 2 FROZEN_DROP. A distinct disposable root child, without requesting the lock, removed the scoped nft table. The kernel ruleset again matched the empty original. The journal STILL said FROZEN_DROP while the **same persistent client socket** successfully sent an 11-byte UDP BYPASS payload and received the server echo. The test proved real ROOT_ADVERSARY_SAME_KERNEL_UNDER_CONTROLLER_FLOCK and ROOT_PACKET_BYPASS_WHILE_LEDGER_SAYS_FROZEN. It later verified exact observable original rules and journal generation 3, but **the intervening kernel change was performed by the independent actor, not protected by the controller**.

**Interpretation:** advisory flock + ordinary fsync CAS cannot enforce the privileged root descendant fence, even if the controller believes the generation is frozen. This test used a disposable adversarial root process, NOT actual S97/S98/S99/watchdog/cron and NOT a physical router. It is a negative safety witness, not an authorization to bypass production controls.

## Versioned privileged legacy actors and physical recovery

RC41 seven-actor source gate [42343250631](https://github.com/ment2/keenetic-vpn/actions/runs/42343250631) PASS 10/10, and full offline 798/798 at run 42343250508. It distinguishes S97 global killall, S98 WiFi TPROXY/route writes, S99/watchdog restart, conditional recovery cron, and current xray-safe-hourly STAGED_ONLY. None has been physically restrained by an independent mandatory kernel mechanism. Root cgroup-v1 escape was observed earlier in disposable RC11; a cooperating flock cannot close this gap.

RC38 physical inventory: the current on-router backup depends on USB; the root filesystem is read-only; /tmp is volatile. RC39 HA off-device encrypted SSH backup/restore is not proven and no independently tested USB-free cold boot rescue exists. Local runner fsync is never an acceptable substitute.

## Confirmed CI inventory and honest release decision

- RC42 real isolated nft DROP/rollback: 42343962946 SUCCESS, 16/16 focused.
- RC42 independent root actor overriding controller lock: 42344147959 SUCCESS, 5/5 focused.
- Full branch offline source contracts at root-adversary commit: [42344147955](https://github.com/ment2/keenetic-vpn/actions/runs/42344147955) SUCCESS **819/819**.
- Underlying RC41 pinned upstream private map: 42342992003 SUCCESS; 42343250631 SUCCESS 10/10.
- Runtime future release conditions remain **unverified**: complete independently attested private owner inventory for the live uninstrumented legacy Xray, packet-preserving atomic ingress freeze/commit and old/new session handover, kernel-bound durable generation CAS and power-loss recovery, mandatory independent privileged root descendant fencing of all seven actors, exact rollback under real root contention, real vendor Linux 4.9 appliance, USB-free physically rehearsed rescue.

**Final: HARD_NO_GO_PRODUCTION.** No Keenetic jobs, production/main/snapshot, Cloudflare, real appliance firewall/routes/cron, merge/deploy, live trial or avoidance of restrictions. Every nft, root and packet operation above was confined to a fresh GitHub runner network namespace. No claim of full seamless VPN pool migration is made.
