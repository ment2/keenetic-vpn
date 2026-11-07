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
**UNVERIFIED until specific RC41 CI completes.** On failure capture exact log/compile reason and retain HARD NO-GO. Even all green test-only instrumentation cannot authorize production. No Keenetic jobs, main/snapshot/Cloudflare, physical firewall/routes/cron, merge, deploy or live trial.
