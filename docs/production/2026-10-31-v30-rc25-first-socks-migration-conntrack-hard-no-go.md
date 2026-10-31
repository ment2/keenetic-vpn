# RC25: first legacy SOCKS → API Xray migration, negative kernel conntrack result

Date: 2026-10-31. Repository: `ment2/keenetic-vpn`. Branch only: `feature/xray-v30-stable-tcp-ingress-lab-20261031`.
Scope: **seamless VPN pool refresh only**. No Keenetic jobs, production/main/snapshot/Cloudflare/firewall/routes/cron, merge, deploy or live trial. Network namespace NAT commands below ran **only inside ephemeral `unshare --net` on GitHub runner**. No host/production firewall modification.

## Why this experiment matters

RC24 [41235943877](https://github.com/ment2/keenetic-vpn/actions/runs/41235943877) already proved real Xray 26.2.6 MIPS32LE API `bo/ado` on synthetic pool: sticky working A; changed new TCP flows to C; old A flow survived; dead C new flows blocked; explicit rollback; same Xray PID/start-ticks and SOCKS port. **Existing production Xray has no API enabled.** First migration of the currently occupied SOCKS/TPROXY ingress remains the blocker.

RC25 attempts a candidate first migration of the **SOCKS TCP 10808 component only**, with the actual old Xray (NO API) still running on original port 10808 and a real API-enabled MIPS32LE Xray on 20808. A disposable loopback-only Linux network namespace with no external NIC or default route uses a test-only `nat OUTPUT` REDIRECT for newly arriving connections to 10808. Pre-existing old TCP must remain attached to legacy Xray. A cooperating test-only watchdog acquires the same `flock`; actual privileged S97/S98/S99/watchdog/cron are NOT fenced by this test. TPROXY UDP ingress is NOT moved, so even a SOCKS pass would not authorize production.

All Xray binaries pinned: Xray 26.2.6 MIPS32LE official ZIP SHA256 `1590b2bcefe64fb0604f29c8c75219bfbe8f63daa3bc8e3956edfa6da97c5869`, binary `3d2588c5ef770a6a7e1bfdd5db511130fb3acd79eb91bfcb108753b3e1dda1f6`. Only 127.0.0.1 synthetic TCP echo destinations A/B.

## Actual CI results

- [RC25 41236773974](https://github.com/ment2/keenetic-vpn/actions/runs/41236773974): FAILURE before jobs, due to YAML unquoted colon in a step name. Corrected in commit `86f1da923cc560d835d60f703deec98e972eed7f`.
- [RC25 41236807375](https://github.com/ment2/keenetic-vpn/actions/runs/41236807375): **FAILURE with genuine TCP interruption**. Before switch: `LEGACY_SOCKS_10808_TCP_ESTABLISHED_NO_API`. After installing netns-local NAT redirect, new SOCKS connected to candidate B but the pre-existing old TCP `echo(old_flow, "old-still-working")` threw `ConnectionResetError: [Errno 104] Connection reset by peer`. **No seamless claim possible.**
- [RC25 41236906116](https://github.com/ment2/keenetic-vpn/actions/runs/41236906116): FAILURE due to outdated static-test assertion after experimental conntrack pretracking change; not a packet outcome.
- [RC25 41236917866](https://github.com/ment2/keenetic-vpn/actions/runs/41236917866): FAILURE `HARD_NO_GO_OLD_TCP_CONNTRACK_NOT_ESTABLISHED_BEFORE_SWITCH`. Test refuses reroute when old flow cannot be proven conntracked. Pre-installed harmless netns-local NAT OUTPUT RETURN rule before old socket created, but no established conntrack witness.
- [RC25 41236987449](https://github.com/ment2/keenetic-vpn/actions/runs/41236987449): **FAILURE with definitive diagnostic**, same prior gate. `RC25_DIAG: CONNTRACK_RC 0`; `RC25_DIAG: CONNTRACK_TCP_LINES ''`; `conntrack v1.4.8: 0 flow entries have been shown.`; test-only NAT OUTPUT rule exists. There is no verified protected conntrack entry for the legacy TCP flow in this QEMU user-mode + native runner netns fixture. Do **not** bypass the protection gate or treat old-flow survival as probable.
- [Offline 41236917805](https://github.com/ment2/keenetic-vpn/actions/runs/41236917805): **SUCCESS 624/624** source/offline contracts at commit `20341bbbaef02c5517f0a0ee8b9488da40d6eee7`. Synthetic test success **does not** override real failed TCP handover.
 
## Actual failure and next narrowly scoped investigation

The proposed same-port first cutover by adding a netns NAT OUTPUT redirect **cannot be certified seamless** in this CI fixture. The old legacy connection already suffered a real RST once; attempts to pretrack old TCP before switching returned **zero conntrack records**. This result does not prove every Linux kernel/NAT design is impossible; it conclusively rejects this implementation until a **positive independent old-flow preservation and conntrack/packet witness** exists. The proof for SOCKS would still be incomplete for real TPROXY TCP+UDP and real production privileged legacy watchdog.

To continue safely in strictly disposable CI, investigate either: (a) independently positive local loopback TCP conntrack capture before first cutover (per-netns raw table / nft-vs-legacy and exact socket identity), then prove existing session byte equality after NEW-only redirect; **or** (b) an alternative migration with stable ingress that genuinely preserves old socket owner and new-only acceptance, with proof under real native kernel. The candidate may remain on a distinct port; never invoke production `killall xray`. If old TCP cannot survive with verified packet witnesses, keep `HARD_NO_GO`.

## Release gate

`RC25_FIRST_SOCKS_MIGRATION_HARD_NO_GO_LEGACY_TCP_RESET_AND_UNTRACKED_CONNTRACK`
`HARD_NO_GO_PRODUCTION`

RC24 MIPS API seamless *subsequent pool refresh* remains proven. RC25 *first migration* does not. Production Xray remains unchanged; no deployment permission granted or inferred.
