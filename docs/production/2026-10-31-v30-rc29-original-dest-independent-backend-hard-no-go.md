# RC29: true MIPS49 original-destination Xray to independent backend netns

Date 2026-10-31. Only feature branch: `feature/xray-v30-stable-tcp-ingress-lab-20261031`.

Following real RC28 [41237924657](https://github.com/ment2/keenetic-vpn/actions/runs/41237924657) SUCCESS positive isolated TAP UDP (25 bytes), but NO host UDP reply through original restricted SLIRP hostfwd, RC29 attempts a separate unshare namespace L2 bridge, TAP, and a Linux backend process in a second `unshare --net` backend namespace at `10.77.0.3:19301`.

Host injects packets originally addressed to backend `10.77.0.3:19301` via MIPS Xray guest `10.77.0.2` using a **disposable-only /32 route**. Real MIPS Linux4.9 guest TPROXY mark + policy local route catches TCP and UDP, official SHA-pinned MIPS32LE Xray uses `freedom` with **NO synthetic redirect**, dials original foreign IP:port to backend isolated from its kernel sockets. Separate backend must receive exact TCP/UDP payload and host must receive exact replies; real TPROXY counters and UID65534/CAP_NET_RAW/no_new_privs are required. SLIRP `restrict=on` stays enabled, but actual traffic uses independent TAP, never claims SLIRP hostfwd return.

**Verified actual GitHub Actions:** [RC29 41238192710](https://github.com/ment2/keenetic-vpn/actions/runs/41238192710) **SUCCESS**, job `124646302601`, source commit `2af102cd8ef4297ef4f354782d733dc69c4ef5d9`. All jobs steps including 4/4 static tests, actual QEMU MIPS32LE Linux4.9 independent backend networking and artifact upload were SUCCESS. Log witnesses:
- `RC29_HOST: REAL_MIPS_XRAY_TCP_ORIGINAL_DEST_RESPONSE 22`
- `RC29_HOST: REAL_MIPS_XRAY_UDP_ORIGINAL_DEST_RESPONSE 22`
- `RC29_BACKEND: ORIGINAL_DEST_TCP_ECHO_EXACT ('10.77.0.2', 42962) 22`
- `RC29_BACKEND: ORIGINAL_DEST_UDP_ECHO_EXACT ('10.77.0.2', 37034) 22`
- `RC29_GUEST_REAL_XRAY_CAP_NET_RAW_NNP_READY` and `RC29_GUEST_REAL_XRAY_ORIGINAL_DEST_TPROXY_COUNTERS_POSITIVE`
- `RC29_PASS_REAL_MIPS49_XRAY_TCP_UDP_ORIGINAL_DEST_INDEPENDENT_BACKEND`.
Also [offline CI 41238192864](https://github.com/ment2/keenetic-vpn/actions/runs/41238192864) **SUCCESS, 648/648**. The new packet path **does not use SLIRP hostfwd**; the SLIRP UDP return remains unproven and failed prior positive controls. The RC29 backend does not remain alive for a post-Xray-death canary test, so **the RC29 topology's no-direct-fallback after death is not yet proven**. Original destination, independent backend TCP/UDP and host return **are** proven in this bounded TAP setup; no hardware/VPN authorization follows.

Even if this proof passes, privileged legacy S97/S98/S99/watchdog/cron root descendants, generation CAS/hardware enforcement, root cgroup-v1 escape, full DNS/IPv6 no-leak, device vendor kernel and physical independent USB-free power-loss rescue remain unverified.

**HARD_NO_GO_PRODUCTION**, no Keenetic jobs or production/main/snapshot/Cloudflare/real routes/firewall/cron/merge/deploy/live trial.
