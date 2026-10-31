# RC29: true MIPS49 original-destination Xray to independent backend netns

Date 2026-10-31. Only feature branch: `feature/xray-v30-stable-tcp-ingress-lab-20261031`.

Following real RC28 [41237924657](https://github.com/ment2/keenetic-vpn/actions/runs/41237924657) SUCCESS positive isolated TAP UDP (25 bytes), but NO host UDP reply through original restricted SLIRP hostfwd, RC29 attempts a separate unshare namespace L2 bridge, TAP, and a Linux backend process in a second `unshare --net` backend namespace at `10.77.0.3:19301`.

Host injects packets originally addressed to backend `10.77.0.3:19301` via MIPS Xray guest `10.77.0.2` using a **disposable-only /32 route**. Real MIPS Linux4.9 guest TPROXY mark + policy local route catches TCP and UDP, official SHA-pinned MIPS32LE Xray uses `freedom` with **NO synthetic redirect**, dials original foreign IP:port to backend isolated from its kernel sockets. Separate backend must receive exact TCP/UDP payload and host must receive exact replies; real TPROXY counters and UID65534/CAP_NET_RAW/no_new_privs are required. SLIRP `restrict=on` stays enabled, but actual traffic uses independent TAP, never claims SLIRP hostfwd return.

**CI pending actual completion.** On any network topology, socket bind, packet or QEMU failure, record the marker, retain HARD NO-GO and do not claim success.

Even if this proof passes, privileged legacy S97/S98/S99/watchdog/cron root descendants, generation CAS/hardware enforcement, root cgroup-v1 escape, full DNS/IPv6 no-leak, device vendor kernel and physical independent USB-free power-loss rescue remain unverified.

**HARD_NO_GO_PRODUCTION**, no Keenetic jobs or production/main/snapshot/Cloudflare/real routes/firewall/cron/merge/deploy/live trial.
