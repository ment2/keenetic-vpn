# RC28 MIPS49 isolated TAP vs SLIRP UDP reverse-path control

Date 2026-10-31. Same feature branch only.

RC23 [41235004868](https://github.com/ment2/keenetic-vpn/actions/runs/41235004868) **FAILURE**: real MIPS Linux4.9 no Xray/no TPROXY guest received and sent six 25-byte UDP packets, but host SLIRP hostfwd saw no reply with restrict=on. Positive control is unproven.

RC28 tests a second independent QEMU PCnet/TAP NIC entirely inside fresh `unshare --net` alongside first QEMU SLIRP NIC, which keeps `restrict=on`. No external NIC/default route is present. TAP host/guest private link checks exact TCP and UDP payload and UDP peer; SLIRP hostfwd is checked independently. TAP success would prove only private TAP UDP, never SLIRP UDP nor Xray, and is NOT original-destination evidence.

RC28 real disposable [GitHub Actions 41237924657](https://github.com/ment2/keenetic-vpn/actions/runs/41237924657) at source `4962a81cc63c312e04bc14009ce36b6ab4b15fab`: **SUCCESS**. All four static tests PASS, real MIPS QEMU and artifact upload PASS. Host `PRIVATE_TAP_BIDIRECTIONAL_UDP_EXACT_RECEIVED 25`; private TAP TCP PASS. Original restricted SLIRP TCP PASS, UDP timeouts 1/2/3 with `SLIRP_UDP_RETURN_UNPROVEN_DESPITE_TAP_CONTROL`. Guest independently reported UDP receive and sendto on both 10.77.0.1 private TAP peer and 10.0.2.2 SLIRP peer. This is a **positive TAP transport proof** and a separately observed negative SLIRP hostfwd result; it does **not** certify bidirectional UDP through SLIRP or Xray. No genuine independent-backend original-destination Xray without synthetic freedom.redirect has been established. RC25 first migration old-flow conntrack remains zero; RC27 SYN-only variant still experimental. Seven root-privileged legacy S97/S98/S99/watchdog/cron spawners remain unfenced, actual root cgroup escape recorded, hardware USB-less rescue unverified.

**HARD_NO_GO_PRODUCTION.** No Keenetic jobs, production/main/snapshot/Cloudflare/real firewall/routes/cron/merge/deploy/live trial.
