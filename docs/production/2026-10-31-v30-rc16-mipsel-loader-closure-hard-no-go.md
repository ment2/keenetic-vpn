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
