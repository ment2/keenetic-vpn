# RC28 MIPS49 isolated TAP vs SLIRP UDP reverse-path control

Date 2026-10-31. Same feature branch only.

RC23 [41235004868](https://github.com/ment2/keenetic-vpn/actions/runs/41235004868) **FAILURE**: real MIPS Linux4.9 no Xray/no TPROXY guest received and sent six 25-byte UDP packets, but host SLIRP hostfwd saw no reply with restrict=on. Positive control is unproven.

RC28 tests a second independent QEMU PCnet/TAP NIC entirely inside fresh `unshare --net` alongside first QEMU SLIRP NIC, which keeps `restrict=on`. No external NIC/default route is present. TAP host/guest private link checks exact TCP and UDP payload and UDP peer; SLIRP hostfwd is checked independently. TAP success would prove only private TAP UDP, never SLIRP UDP nor Xray, and is NOT original-destination evidence.

RC28 workflow pending. No genuine independent-backend original-destination Xray without synthetic freedom.redirect has been established. RC25 first migration old-flow conntrack remains zero; RC27 SYN-only variant still experimental. Seven root-privileged legacy S97/S98/S99/watchdog/cron spawners remain unfenced, actual root cgroup escape recorded, hardware USB-less rescue unverified.

**HARD_NO_GO_PRODUCTION.** No Keenetic jobs, production/main/snapshot/Cloudflare/real firewall/routes/cron/merge/deploy/live trial.
