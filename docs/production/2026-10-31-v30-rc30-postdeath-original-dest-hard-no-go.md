# RC30 independent backend alive post-Xray death, real MIPS49 TCP UDP no-direct attempt

2026-10-31. Branch feature/xray-v30-stable-tcp-ingress-lab-20261031 only.

Input proof: [RC29 CI 41238192710](https://github.com/ment2/keenetic-vpn/actions/runs/41238192710) SUCCESS. True TCP and UDP original destination 10.77.0.3:19301 from real SHA-pinned MIPS Xray through independent TAP to backend Linux namespace. No freedom redirect.

RC30 reuses exact isolation (SLIRP restrict=on and no default route), must verify TCP and UDP baseline first, then the test guest parent verifies its direct child Xray boot ID/PID/start-ticks, terminates and reaps only that child, witnesses listener disappearance and signals host. Original backend remains **live** during postdeath TCP and UDP canary probes. Strict backend receipt of either unique canary yields HARD NO-GO. Host must receive no canary reply; both real guest TPROXY rule counters must increase after death, else test also fails closed.

**CI unverified until actual run completes**; do not relabel a failure as success. Even a positive result is ONLY bounded original-dest no-fallback on isolated TAP. It cannot prove global IPv6/DNS, SLIRP hostfwd, privileged real watchdog actors or physical rescue.

**HARD_NO_GO_PRODUCTION**: RC11 actual privileged cgroup v1 root escape; seven S97/S98/S99/watchdog/cron root paths not physically fenced; vendor NDM kernel/USB-independent boot and rescue not tested; no production/mutable bridge, Cloudflare, main, real firewall/routes/cron, router jobs, deploy, merge, live trial.
