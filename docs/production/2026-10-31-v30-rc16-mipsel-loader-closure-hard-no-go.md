# RC16 disposable MIPS32LE userland dependency-closure probe (no packet-path claim)

Date: 2026-10-31. Branch `feature/xray-v30-stable-tcp-ingress-lab-20261031`. No router jobs.

The RC14 full-system + native + offline triad has SUCCESS on commit `18d116ddb1e5c5d916ee5ae71caaff55455d82fb`, workflow run 41230151165. RC15 SHA-pinned Debian Stretch MIPS32LE archive downloads identify:
- iptables `b0bd6d7e4bc7da38672b223cb428315309979a19e008aedafb17253315178b67`
- iproute2 `c0b0886583db81db0a517e0945be52d23dcc3ee5fe8ea068bfdaa80cb639213d`
- busybox-static `0c7e287104914e654a2555e9900302180ff54d1ef17e9faf585529e6eadac8e0`

`xray-v30-rc16-mips-dependency-closure.yml` verifies each archive's SHA256 before extracting and reads *foreign ELF metadata only*. The test identifies needed shared libraries and the ELF interpreter that **are not provided by these three exact packages**; it never launches MIPS userland. A missing dependency is a concrete **prerequisite blocker** for a full guest packet test, not evidence that Linux4.9 xt_TPROXY itself fails. RC13 has independently proven in-guest loading of all seven MIPS netfilter .ko.

Next: pin exact hashes for every missing Debian mipsel library package and verify complete loader closure; provision disposable guest NIC or veth/netns, boot same MIPS Linux4.9, run iptables/iproute2 with verified libraries, policy route and real Xray inbound. Verify TCP and UDP bytes and counters, crash no-fallback, IPv6/DNS no-leak. No MIPS full packet result must be claimed until that live isolated experiment succeeds.

Separately, *privileged* legacy cgroup v1 escape was observed in RC11, and full S97/S98/S99/watchdog/cron containment plus independent USB-absent physical boot/rescue and vendor NDM5 certification are not proven.

**HARD_NO_GO_PRODUCTION**. No production/main/snapshot/Cloudflare/firewall/routes/cron/merge/deploy/live trial.

## Verified CI results and precise unresolved dependency witness

- [RC14 full three-way isolated regression CI 41230585901](https://github.com/ment2/keenetic-vpn/actions/runs/41230585901): **SUCCESS** at `fdf8b6c8`; 573/573 offline tests, real native x86_64 TCP/UDP TPROXY, Debian Linux4.9 x86_64 QEMU full-system three two-boot rescue cases. This is not MIPS full packet path.
- [RC15 Debian MIPS32LE package discovery CI 41230585893](https://github.com/ment2/keenetic-vpn/actions/runs/41230585893): **SUCCESS**. Exactly pinned archive SHA256 and MIPS32 little-endian ELF for `/bin/ip`, `/sbin/iptables`, `/bin/busybox`; relative guest symlinks permitted, absolute host-exiting symlinks excluded. No foreign MIPS executable run.
- [RC16 MIPS32LE dependency-closure CI 41230670098](https://github.com/ment2/keenetic-vpn/actions/runs/41230670098): **SUCCESS** for a deliberate *negative* dependency closure test, not a MIPS networking test. Within **only the three extracted SHA256-pinned archive packages**:
  - `ip` missing `ld.so.1`, `libc.so.6`, `libdl.so.2`.
  - `iptables` missing `ld.so.1`, `libc.so.6`, `libip4tc.so.0`, `libip6tc.so.0`, `libm.so.6`, `libxtables.so.12`.
  - `busybox-static` has no missing dynamically linked dependencies.
- **Meaning:** exact additional MIPS userland library package SHA256s, loader/interpreter ABI, extension path and dependent guest execution are not yet demonstrated. An attempted TPROXY packet-path test now would lack prerequisite MIPS userland; negative evidence cannot establish actual kernel TPROXY failure.

### Release decision

**RC16 DISPOSABLE DEPENDENCY INVENTORY PASS, END-TO-END MIPS TCP/UDP UNTESTED, HARD_NO_GO_PRODUCTION.** Privileged legacy root cgroup v1 escape and physical USB-independent boot/power/no-leak acceptance remain independent HARD NO-GO gates. No new router jobs, changes to production/main/snapshot/Cloudflare/firewall/routes/cron, merge/deploy/live trial.
