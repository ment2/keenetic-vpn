# RC35 | Real MIPS Linux 4.9 UDP conntrack expiry with still-open old client; first cutover must be refused

Date: 2026-11-01. Repository `ment2/keenetic-vpn`, **only branch** `feature/xray-v30-stable-tcp-ingress-lab-20261031`. Scope: seamless Xray VPN pool refresh and one-time API-less legacy→API-enabled ingress migration, never production. RC34 had previously proved a briefly silent UDP client could be preserved while its conntrack entry persisted; RC35 tests what happens when that entry expires.

## Real packet/kernel evidence

- [**RC35 MIPS49 Linux4.9 CI 41242972093 SUCCESS**](https://github.com/ment2/keenetic-vpn/actions/runs/41242972093), SHA `e63fbe3fa1748822c450e3645ec7e59a81db2a43`, job `124660490849`. Repeated [**RC35 CI 41243063537 SUCCESS**](https://github.com/ment2/keenetic-vpn/actions/runs/41243063537), with the independent negative gate files present. These are **SUCCESS for expected safe refusal**, not SUCCESS for first production migration.
- Disposable `qemu-system-mipsel` Malta real Debian MIPS32LE Linux 4.9.228, SHA256-pinned kernel/Xray 26.2.6 and loadable `nf_conntrack`, `nf_conntrack_ipv4`, `xt_TPROXY`; `SLIRP restrict=on`; separately isolated backend netns, true original destination `10.77.0.3:19301`; no public network, no real router commands, netfilter or routes.
- Guest `nf_conntrack_udp_timeout` and `nf_conntrack_udp_timeout_stream` **set to 3 seconds inside disposable guest only**, independently read back (intentionally accelerated to induce expiry; NOT production defaults). Both non-root Xray processes retain their PID/start-ticks, old `12345` TPROXY and candidate API-enabled `22345` remain alive.
- Host opens one UDP client socket on local port `40404`, sends exact bytes and receives UDP backend echo while legacy Xray owns TPROXY; guest separately witnesses its **actual nf_conntrack record**. The client socket stays open and sends **no** packets while guest polls. After ~3 sec the guest verifies the entry has **disappeared** from `/proc/net/nf_conntrack`. Only two original legacy TPROXY rules exist; no new candidate rules are added.
- The **same original UDP client socket** then exchanges equal bytes with the independent backend; a new kernel conntrack entry is observed. This shows that **conntrack retention is not guaranteed for the lifetime of an open UDP socket**. It does **NOT** independently establish whether Xray reused its old internal UDP association or created a new one.

Exact log excerpts:
```
RC35_GUEST_CONNTRACK_UDP_TIMEOUTS_THREE_SECONDS_CONFIRMED
RC35_HOST: UDP_EXACT OLD_BEFORE_EXPIRY 26
RC35_HOST: OLD_UDP_SOCKET_HELD_OPEN_WITH_SOURCE_PORT 40404
RC35_GUEST_REAL_OLD_UDP_CONNTRACK_ENTRY_WITNESSED
RC35_GUEST_KERNEL_OLD_UDP_CONNTRACK_EXPIRED_WHILE_BOTH_XRAY_PIDS_UNCHANGED
RC35_GUEST_FAIL_CLOSED_NO_NEW_CANDIDATE_TPROXY_RULES
RC35_HOST: UDP_EXACT OLD_AFTER_EXPIRY_NO_CUTOVER 36
RC35_HOST: SAME_OLD_UDP_SOCKET_EXACT_BYTES_AFTER_CONNTRACK_TIMEOUT
RC35_GUEST_OLD_UDP_ASSOCIATION_RECOVERED_ONLY_WITHOUT_CUTOVER
RC35_HOST: PASS_SAFE_REFUSAL_AFTER_KERNEL_CONNTRACK_EXPIRY
RC35_PASS_REAL_MIPS49_NF_CONNTRACK_EXPIRY_DETECTED_AND_CUTOVER_REFUSED
RC35_HARD_NO_GO_NO_COMPLETE_XRAY_UDP_OWNER_OR_ATOMIC_FREEZE
```

## Fail-closed generation CAS and adversarial legacy fences

- [**Full offline CI 41243086362 SUCCESS 715/715**](https://github.com/ment2/keenetic-vpn/actions/runs/41243086362). New `rc35_freeze_cas_disposable_model.py` uses an in-memory lock and immutable prepare snapshot to model boot-ID/generation CAS, matching old client/kernel/Xray UDP identities, kernel-freeze/independent-root-fence receipts, owner-commit acknowledgment and exact rollback. Eight tests mutate expired/missing kernel flows, absent Xray owner, missing independent root fence, stale generation/boot, missing kernel ack, nonrestored rules and simultaneous proposals. Synthetic success **never** authorizes production.
- Prior [RC34 full offline 701/701](https://github.com/ment2/keenetic-vpn/actions/runs/41241373279) included negative gates for all seven versioned privileged legacy S97/S98/S99/watchdog/cron actors and descendants: root cgroup-v1 escape, orphan processes, forged kernel denial, missing socket owner cookie and stale boot/PID/start-ticks. **These are negative contract tests, not independently enforced real root fencing.**

## Concrete blockers to seamless release

1. **Kernel conntrack expires while an old UDP client is still open.** This has now been demonstrated in full-system QEMU. It is not a complete old-flow authority. A dormant old Xray UDP association (if it exists) cannot safely be declared new solely because a kernel conntrack entry disappeared.
2. **No complete independently verified Xray internal UDP association inventory** (source/destination/protocol/ingress interface, socket cookie, exact process PID/start-ticks and generation) has been obtained from the running legacy Xray. Real Xray API that was previously tested for outbound pool BO/ADO is not proof of internal UDP session enumeration.
3. **No atomic kernel freeze/owner switchover, durable CAS or kernel-acknowledged rollback** in the existing first-cutover design. RC35 model is deliberately in-memory and QEMU expiry negative does not implement freeze. Any silent association omitted from the old pin map could be stolen by broad candidate UDP routing.
4. **No independent physical privileged root fencing.** S97 killall, S98 TPROXY modifications, S99/watchdog/cron restarts and root descendants escaping cgroup v1 have not been contained with enforceable hardware/boot-time fences. No vendor KN-1810 4.9-ndm-5, USB-free power-loss rescue or authenticated real VLESS/REALITY acceptance.

Decision:
- `RC35_PASS_REAL_MIPS49_NF_CONNTRACK_EXPIRY_DETECTED_AND_CUTOVER_REFUSED` **verified disposable negative**.
- `RC35_OFFLINE_FREEZE_CAS_ADVERSARIAL_715_SUCCESS` **simulator only**.
- **`HARD_NO_GO_PRODUCTION`**. No Keenetic jobs, production/main/snapshot/Cloudflare changes, real firewall/routes/cron, merge/deploy/live trial.

Only next relevant work: independently verify legacy Xray UDP association ownership and kernel-fenced atomic owner transition, or keep the exact HARD NO-GO. Do not invent Xray APIs or claim successful physical fencing from synthetic receipts.
