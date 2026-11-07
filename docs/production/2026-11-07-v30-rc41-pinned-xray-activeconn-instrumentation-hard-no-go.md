# RC41 | Pinned Xray 26.2.6 instrumented private UDP map in disposable CI: release hard no-go

Date 2026-11-07. Repository `ment2/keenetic-vpn`, branch `feature/xray-v30-stable-tcp-ingress-lab-20261031` exclusively. **HARD_NO_GO_PRODUCTION**. No production or router operations.

## What RC40 really established
[RC40 real MIPS49 CI 42295498150](https://github.com/ment2/keenetic-vpn/actions/runs/42295498150) SUCCESS: two real UDP sockets with distinct Linux SO_COOKIE/inode; A was previously dispatched through the old Xray, became kernel-conntrack-invisible but remained in Xray, and B was never sent and had no Xray association. Kernel conntrack+recent packets saw neither at snapshot. When sent again, A was reused and B newly processed, demonstrated with actual packets and pinned upstream debug. [RC40 source CI 42294794432](https://github.com/ment2/keenetic-vpn/actions/runs/42294794432) 781/781 SUCCESS; owner negative 42294794557 8/8 SUCCESS. This is bounded **negative inventory evidence**, not successful cutover.

## RC41 real upstream source plan
Checkout upstream Xray-core at exact tag `v26.2.6` and commit `12ee51e4bb1d02ece4ef4b7114efa2bcdc130995`. Check five source Git blob object IDs against known verified hashes. Copy a **single test-only Go source file** into `app/proxyman/inbound`; do not change any upstream production source or build a patched production binary. Compile that package's test binary and run it as UID 65534 in disposable GitHub CI's new network namespace with loopback only and no external/default route.

The real original `udpWorker.Start` binds a Linux UDP listener; two Linux clients have independent SO_COOKIE values (the upstream udp.Hub keeps its own transport socket private, and no hub SO_COOKIE is claimed). Xray's original `udpWorker.callback`, `getConnection`, and private `activeConn` map handle actual echo packets via a minimal disposable test-only proxy. The test observes the private map under its own `RWMutex`, attests PID, process start-ticks and kernel boot ID, verifies A idle association reuse, then sends B after capture to prove a source-level snapshot is immediately stale without an ingress kernel freeze. Another test artificially advances `lastActivityTime` to test the pinned Xray source's 120-second inactivity cleaner without actually waiting two minutes.

**Not claimed:** independent process ownership of all legacy UDP flows; kernel nf_conntrack expiry in this exact Go test (already proven by RC40 separate real MIPS test); per-flow Xray socket cookie (one shared UDP listener cookie is not a per-association cookie); durable generation CAS, kernel freeze/commit, rollback under actual root descendants; off-USB physical rescue or vendor kernel acceptance. The currently running uninstrumented legacy Xray has no supported gRPC activeConn listing in the three source-pinned services. A test compiled into another process cannot read its private map; instrumentation does NOT prove impossibility of future kernel tracing or custom sanctioned builds.

## Privileged root and physical gates
Existing source-based S97/S98/S99/watchdog/cron checks and advisory-lock counterexamples remain **negative-only**. Root cgroup-v1 escape from RC11 has not been physically contained. In RC38, backup is USB-dependent and root is read-only; RC39 off-device HA transfer and authenticated encrypted restore remain unverified. No code here is a real mandatory kernel policy or physical USB-less rescue test.

## Result
**Verified source-bounded outcome:** [RC41 real pinned upstream test CI 42342992003](https://github.com/ment2/keenetic-vpn/actions/runs/42342992003) **SUCCESS**, source SHA `24af4848e92a50c70fad77915f7fff4ba4660729`; all CI steps green. The actual `go1.25.7` build of Xray-core v26.2.6 succeeded; the test-only binary ran under UID65534 in `unshare --net` with loopback up and no default route. Exact logs:
```
RC41_PINNED_UPSTREAM_XRAY_26_2_6_SHA_VERIFIED
RC41_UPSTREAM_REAL_GO_PACKAGE_COMPILED_TEST_ONLY
RC41_ISOLATED_KERNEL_LOOPBACK_NO_DEFAULT_ROUTE
RC41_REAL_XRAY_PACKET_ECHO A_INITIAL bytes=28
RC41_REAL_INPROCESS_UDP_INVENTORY_A boot=97d28c6a-8f34-46ff-ab96-edea19c1f1e2 pid=5945 ppid=5938 ticks=8717 a=34919 cookie=1 b=47176 cookie=2
RC41_REAL_XRAY_PACKET_ECHO A_AFTER_IDLE bytes=31
RC41_REAL_XRAY_PACKET_ECHO B_NEW_AFTER_SNAPSHOT bytes=39
RC41_REAL_XRAY_SOURCE_PRIVATE_ACTIVE_CONN_A_IDLE_REUSED_B_CREATED
RC41_REAL_LINUX_CLIENT_UDP_SOCKET_COOKIES_WITNESSED
RC41_PRIVATE_SNAPSHOT_RWLOCK_IS_NOT_KERNEL_INGRESS_FREEZE
RC41_UNINSTRUMENTED_LEGACY_PROCESS_NOT_INSPECTED_OR_MODIFIED
RC41_PRIVATE_XRAY_WORKER_120S_CLEANER_TEST_ONLY
RC41_PASS_REAL_INPROCESS_XRAY_WORKER_PACKET_AND_PRIVATE_MAP_BOUNDED_ONLY
RC41_HARD_NO_GO_NO_EXTERNAL_LEGACY_INVENTORY_KERNEL_FREEZE_ROOT_FENCE_USB_RESCUE
```
The first test made real UDP socket A initially dispatch through pinned Xray `udpWorker`, retained it after 4 seconds silence, and after a read-locked snapshot sent B so the private map grew from 1 to 2. The second test advanced only the test-worker `lastActivityTime` by 121s and used the authentic Xray `clean()` method; it does **not** prove natural 120s inactivity on hardware. Socket cookies belong to two **client** sockets; the shared `udp.Hub` transport's own unexported socket cookie was **not** read, so no per-private-connection kernel-cookie mapping is proved. The full live legacy UDP inventory and 3s kernel conntrack expiry were not tested together in this run (RC40 separately proves the latter). The snapshot does not include packet ingress interface or authenticated kernel freeze generation.

[Full offline CI 42342867647](https://github.com/ment2/keenetic-vpn/actions/runs/42342867647) **SUCCESS 788/788** on source `f7656f259d5951df710335c373c045af87e975e6`, covering RC41 source isolation/negative claims; no unrelated source changes were made after that to these structural tests apart from UID65534 executable staging in disposable `/tmp`.

Exact failures NOT to relabel: [42342726449](https://github.com/ment2/keenetic-vpn/actions/runs/42342726449) **FAILURE** (unused Go import and illegal `udp.Hub.udpConn` package-private field access); [42342823993](https://github.com/ment2/keenetic-vpn/actions/runs/42342823993) **FAILURE** (only private field access remained); [42342867665](https://github.com/ment2/keenetic-vpn/actions/runs/42342867665) **FAILURE** (Go compilation succeeded, but test binary under runner-private temp was inaccessible to UID65534). Commits `f7656f25` and `24af4848` repaired these issues without relaxing root/container isolation.

**Release decision remains `HARD_NO_GO_PRODUCTION`.** A test added to the **new** upstream checkout can inspect that checkout's private `udpWorker`, but cannot retroactively enumerate activeConn from existing production API-less legacy PID. The three pinned gRPC services do not expose such a snapshot. No physical kernel-enforced ingress freeze/owner commit and rollback, durable generation CAS with process/socket attestation, root descendant S97/S98/S99/watchdog/cron hardware fence, vendor KN-1810 acceptances or USB-free boot/rescue were demonstrated. A signed, verified cold-boot recovery mechanism remains mandatory before any production change. On failure capture exact log/compile reason and retain HARD NO-GO. Even all green test-only instrumentation cannot authorize production. No Keenetic jobs, main/snapshot/Cloudflare, physical firewall/routes/cron, merge, deploy or live trial.
