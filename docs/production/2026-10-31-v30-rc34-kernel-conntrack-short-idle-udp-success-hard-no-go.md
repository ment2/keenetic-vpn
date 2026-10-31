# RC34 | Conntrack-aware first TPROXY cutover: short-idle UDP survives; general seamless pool HARD NO-GO
Date: 2026-10-31. Repository: `ment2/keenetic-vpn`. Branch: `feature/xray-v30-stable-tcp-ingress-lab-20261031` ONLY.

## User objective
Seamlessly refresh VPN server pool. First migration must preserve preexisting SOCKS/TPROXY TCP+UDP sessions while new flows move to an API-enabled Xray, with exact rollback, no direct bypass, durable boot/generation CAS and independently verified privileged S97/S98/S99/watchdog/cron fencing. No production, main/snapshot, Cloudflare, Keenetic jobs, physical firewall/routes/cron, merge/deploy or live trial.

## Verified full-system MIPS49 result
[**RC34 run 41241511914**](https://github.com/ment2/keenetic-vpn/actions/runs/41241511914) **SUCCESS**, commit `4d0feea514eac211f2dfbf9d4b4a3b867d22b877`. Disposable QEMU Malta actual Debian MIPS32LE Linux 4.9.228, SHA256-pinned Xray 26.2.6, real xt_TPROXY + nf_conntrack + nf_conntrack_ipv4 modules, independent backend `10.77.0.3:19301`, no Freedom redirect, SLIRP `restrict=on`, and isolated netns-only firewall/routes. Old Xray has no API and retains TPROXY 12345; independent candidate Xray has loopback API listener 21808 and TPROXY 22345. Both retain PID/start-ticks. The test does NOT call the Xray gRPC routing API itself (that was tested separately in RC24).

Three OLD UDP sockets:
- First was actually primed **before** AF_PACKET observation (source port `38754`), then deliberately silent through observer snapshot.
- Two active UDP source ports `39796` and `57705` were seen by AF_PACKET; all three were retained in the actual Linux4.9 guest `/proc/net/nf_conntrack` snapshot.
- The guest cross-checked active AF_PACKET tuples against the kernel snapshot, required **three** independent matching source/destination/port/protocol records, pinned old traffic to the original legacy Xray before broad candidate UDP, and demanded positive xt_TPROXY counters on **six** migration rules. The exact MIPS original-destination backend returned equal TCP/UDP bytes.
- After cutover the previously silent old socket resumed successfully via old ownership, as did the other old TCP/UDP flows. A new TCP+UDP flow reached the candidate. After rollback, old and new TCP/UDP matched again, and only the two original legacy TPROXY rules remained.
- The guest checked its boot ID and staged generation values, but this was **disposable in-memory/snapshot logic, NOT atomic durable cross-process CAS**. No kernel-enforced ingress freeze during enumeration, Xray internal flow inventory, physical rescue or vendor 4.9-ndm-5 acceptance.

Exact selected CI log witnesses:
```
RC34_HOST: UDP_EXACT OLD_IDLE_PRIMED 24
RC34_HOST: SILENT_PREEXISTING_UDP_SOURCE_PORT 38754
RC34_HOST: TWO_PACKET_ACTIVE_UDP_SOURCE_PORTS (39796, 57705)
RC34_GUEST_KERNEL_CONNTRACK_RETAINED_THREE_OLD_UDP_ASSOCIATIONS_ONE_IDLE
RC34_GUEST_KERNEL_ASSOCIATION_PINS_INSTALLED count=3 boot=3660f442-3044-48d5-a055-a7b6d3be4372
RC34_HOST: UDP_EXACT OLD_IDLE_RESUMED_DURING 32
RC34_HOST: TCP_EXACT NEW_DURING 19
RC34_HOST: UDP_EXACT NEW_DURING 19
RC34_HOST: UDP_EXACT OLD_IDLE_AFTER_ROLLBACK 32
RC34_HOST: PASS_THREE_OLD_UDP_INCLUDING_PREVIOUSLY_IDLE_AND_TCP_CUTOVER_ROLLBACK
RC34_GUEST_TWO_XRAY_PID_STARTTICKS_UNCHANGED_GENERATION_CAS_SYNTHETIC
RC34_PASS_KERNEL_TRACKED_IDLE_UDP_ASSOCIATION_CUTOVER_ONLY
RC34_HARD_NO_GO_DYNAMIC_UDP_5TUPLE_CAS_PRIVILEGED_LEGACY_FENCING_PHYSICAL
```
A UDP pause shorter than a second is not a test of a long-term silent socket or expiry. Kernel conntrack entries are timeout-bound and do not intrinsically state which Xray process owns the associated UDP session or the ingress interface. The **candidate cannot be made production-safe merely by loading nf_conntrack**.

## Negative gates and offline results
[**Full offline 41241373279**](https://github.com/ment2/keenetic-vpn/actions/runs/41241373279) **SUCCESS 701/701**. The additional source-backed offline gates:
- `rc34_conntrack_owner_authority_gate.py` + 6 tests: reject conntrack-only inventory without a complete, independently attested Xray session owner map (PID/start-ticks/socket cookie, boot ID, generation), conntrack timeout missing an existing client socket, absent ingress interface, stale kernel flow owner receipts, un-frozen ingress during commit, absent durable generation CAS, or incomplete rollback. Even all-synthetic-true is `SYNTHETIC_CONTRACT_ONLY`; production_authorized always false.
- `rc34_privileged_actor_fencing_gate.py` + 5 tests: deliberately mutate every one of seven S97/S98/S99/watchdog/cron privileged legacy events, including a root actor ignoring a cooperative lock, forged kernel denial, stale PID/start-ticks/generation/boot, escaped cgroup and orphan processes. This verifies **negative acceptance**, not an actual enforced fence.
- `test_xray_v30_rc34_kernel_idle_udp.py` + 5 structural gates: SHA-pinned kernel modules, actual earlier send before packet observer, separate conntrack readback, old-flow kernel counters and rollback.

The earlier [RC33 actual packet cutover 41240338587](https://github.com/ment2/keenetic-vpn/actions/runs/41240338587) and [RC31 legacy audit 41239253164](https://github.com/ment2/keenetic-vpn/actions/runs/41239253164) remain distinct supporting disposable-only results; they do not verify physical root fencing.

## Concrete outstanding HARD NO-GO
1. **No complete authoritative old Xray UDP association list** (including long-idle sessions) is exposed by the existing production process. Conntrack is neither guaranteed to have seen every old flow since boot nor a process-owner map; it can expire before the application-side UDP session. Without independent Xray association identity/cookie and an exact complete inventory, even a three-flow test cannot establish universal, lossless migration.
2. **No atomic frozen ingress + CAS** during kernel inventory/iptables rule installation. The CI uses staged synthetic generation, not a durable crash-atomic owner journal. A packet arriving between read and rule commit or root restart can escape pinning and be silently misrouted. Future disposable tests require a genuine exclusive kernel ownership transition with packet witnesses and replay/rollback fencing.
3. **Privileged legacy restart escape remains unfenced:** S97 `killall xray`, S98 TPROXY rewrites, S99/watchdog/cron root restarts, and previously observed cgroup-v1 root escape. No physical readback of descendant PID/start-ticks/exec SHA/socket-inodes; no universal mandatory root action fence; no vendor kernel verified hardware cutover or USB-free power-loss rescue.

### Decision
`RC34_MIPS49_KERNEL_CONNTRACK_SHORT_IDLE_UDP_FIRST_CUTOVER_SUCCESS` is **bounded disposable proof**.
`RC34_HARD_NO_GO_COMPLETE_IDLE_UDP_OWNERSHIP_AND_ATOMIC_FENCING`.
**`HARD_NO_GO_PRODUCTION`**.

Next work stays on the main seamless-pool objective: independently verify expiration/untracked UDP ownership and complete Xray session inventory, and obtain actual mandatory privileged restart fencing/physical acceptance before requesting a separately authorized deployment. No changes to actual hardware or services in this phase.
