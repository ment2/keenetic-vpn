# RC36 real Xray UDP session reuse across Linux 4.9 conntrack expiry: acceptance decision

Date 2026-11-01. Scope strictly the existing feature branch `feature/xray-v30-stable-tcp-ingress-lab-20261031`; **HARD_NO_GO_PRODUCTION**.

## Existing independently verified baseline

- [RC33 real AF_PACKET discovered active old UDP flows CI 41240446070](https://github.com/ment2/keenetic-vpn/actions/runs/41240446070) SUCCESS: old TCP and active UDP sessions maintained across known cutover and rollback; dormant flows not inventoried.
- [RC34 real MIPS nf_conntrack dormant short-idle UDP CI 41241511914](https://github.com/ment2/keenetic-vpn/actions/runs/41241511914) SUCCESS: three old UDP flows including one briefly idle pinned while entries persisted.
- [RC35 real nf_conntrack expiry CI 41243063537](https://github.com/ment2/keenetic-vpn/actions/runs/41243063537) SUCCESS for **refusal**: conntrack entry expired with old UDP client socket alive, no candidate cutover performed. [Offline 715/715 CI 41243086362](https://github.com/ment2/keenetic-vpn/actions/runs/41243086362) SUCCESS (simulator only).

## Newly prepared RC36 experiment and independent source audit

Upstream Xray-core 26.2.6 pinned repository commit `12ee51e4bb1d02ece4ef4b7114efa2bcdc130995`. Five exact source Git blob IDs for udpWorker, proxyman/router/stats gRPC and dokodemo must match `git hash-object` before source assertions. Git blob SHA1 is computed on `blob N\\0` plus file bytes; it must not be confused with raw SHA1 or the compiled MIPS binary SHA256.

Source worker has private `udpWorker.activeConn`, keyed by `connID{src,dest}` (conditionally destination for `!cone`), removes inactive entries on periodic check older than 120s; Xray's actual UDP worker ownership is NOT equivalent to kernel `nf_conntrack` (3s here). Three pinned gRPC services do NOT expose a complete live UDP-worker activeConn inventory API. That does **not** exclude custom instrumentation, nor prove live production ownership readback.

RC36 disposable QEMU guest uses native Xray 26.2.6 MIPS32LE and real Linux4.9 xt_TPROXY to independent backend, preserved source UDP socket, real kernel conntrack entry then expiry with short test-only kernel timeout, and then same UDP socket repeated. Log witness `processing connection from: src:port` must occur **once**, not twice, for the preserved old connection; after expiry host/guest bytes, same process PID/start ticks and no cutover are independently enforced. A successful debug-log count is a bounded observation of reused `proxy.Process`, **not** a complete enumeration of all Xray internal worker entries.

**CI result intentionally not claimed until the workflow finishes.** No verified atomic kernel ingress freeze/commit, original full UDP owner inventory, durable boot/generation CAS, root privileged descendant fence, vendor kernel acceptance, independent USB-free rescue, or full DNS/IPv6 no-leak. Even a green RC36 cannot authorize production.

Forbidden and untouched: Keenetic jobs, production/main/snapshot, Cloudflare, real firewall/routes/cron, merge/deploy/live trial, bypass of any safety boundary.
