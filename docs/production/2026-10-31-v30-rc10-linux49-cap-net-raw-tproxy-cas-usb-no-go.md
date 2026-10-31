# Keenetic Xray v30 RC10: real Linux 4.9 full-system Xray, kernel TPROXY raw-only packet flow, 8x3 guardian CAS, no-USB rescue

**Date:** 2026-10-31. **Repo:** `ment2/keenetic-vpn`. **Only branch:** `feature/xray-v30-stable-tcp-ingress-lab-20261031`. **PRODUCTION HARD NO-GO.** No router jobs or tool bypass, production/Cloudflare/main/snapshot/firewall/routes/cron, merge/deploy/live trial.

## Two independently verified real Linux tests

1. [**Linux 4.9 full-system CI 41224765496**](https://github.com/ment2/keenetic-vpn/actions/runs/41224765496): **SUCCESS**, actual QEMU TCG separate **Linux `4.9.0-13-amd64` guest kernel**, three failure scenarios with **two real guest boots each**, real Xray v26.2.6 x86_64. Kernel obtained solely from immutable archived Debian `linux-image-4.9.0-13-amd64_4.9.228-1_amd64.deb`; package SHA256 `d410dd577fac677bb50978d5fe91b622d1520b783cb4ef23a1bcd7851606e326`; extracted `vmlinuz` SHA256 `cc91d3c764694426a4e830da226da61f60a97d074986aa47bb9102ad8792e4c0`. Both exact package bytes and xray release were hash-checked **before VM execution**. **This is Debian 4.9 x86_64, NOT Keenetic `4.9-ndm-5` MIPS32LE!**
2. [**Native real TPROXY CI 41224152158**](https://github.com/ment2/keenetic-vpn/actions/runs/41224152158): **SUCCESS**, separate current GitHub runner Linux x86_64 kernel. Real Xray v26.2.6 ran in **3 disposable network namespaces**, **UID/GID 65534 and only effective `CAP_NET_RAW` mask `0000000000002000`**, with `no_new_privs` and verified PID/start-ticks. Actual IPv4 **TCP and UDP** packets crossed isolated TPROXY iptables mangle, `fwmark` `0x40000000` and policy routing table 100 to the test backend. Isolated FORWARD=DROP and no default Internet route prevented direct fallback **after the Xray child died**. This is a **real packet-path test**, but **NOT on kernel 4.9** and not on the router.
3. Official `Xray 26.2.6 linux/amd64` was verified with SHA256 archive `29ce535b56e207a406ffa1c2d4842dcc410be003eff8ec508bb732abc9f8e385` and executable `3f650abf1fc4a4fbf5abe7fc9990a2658020907cd984214e9c075b4b00989fea`. The real MIPS32LE 8+8 guardian CAS under QEMU **user-mode** was separately proven in prior [CI 41215515431](https://github.com/ment2/keenetic-vpn/actions/runs/41215515431), not the present Linux 4.9 guest.

## Direct capabilities and child ownership on actual Debian Linux 4.9 guest

- `rc10_guest_socket_cap_probe.c` called `PR_GET_NO_NEW_PRIVS` **after `exec`**, receiving **1** in the actual 4.9 guest for both profiles. The older kernel does not expose `NoNewPrivs` in `/proc/<pid>/status`; the direct PR_GET probe avoids a false negative.
- UID/GID 65534 **without** capabilities: TCP and UDP `setsockopt(IP_TRANSPARENT)` denied. Only `CAP_NET_RAW`: both operations passed under the same guest kernel, with exact `CapEff=0x2000`.
- Real official Xray 26.2.6 initialized a TCP+UDP `dokodemo-door` transparent-mode inbound with `followRedirect`. The guest checked the listener, exact PID/start-ticks, effective caps and pre-`exec` NNP setup.
- Separate parent launched another genuine Xray child, fsynced its PID/start-ticks and then sent SIGKILL **only to itself**. Its child's `PR_SET_PDEATHSIG=SIGKILL` terminated the listener. Observer required pinned process identity and no live listener, **without sending any signal to the recorded stale PID**.

## Actual competing guardian generations and aborted durable journal (Linux 4.9)

`xray/lab/rc10_guest_guardian_generation_cas.c` ran under the same Linux 4.9 guest:

- **Three waves of 8 real concurrently awakened guardian child processes**; each opens an independent file description and competes for `flock(LOCK_EX)`, checks the expected committed owner generation and can advance only one generation. **Exactly 1 winner and 7 stale claimants in each wave**, with fsynced generation file, atomic rename and parent-directory fsync.
- An injected owner process was SIGKILLed **after fsyncing PREPARED bytes but before commit/rename**. The committed generation remained unchanged at 2; no replay occurred. The third wave completed recovery by committing generation 3 exactly once.
- This is **guest /run CAS logic**, not a proof of the installed production agent, S97/S98/S99/watchdog/cron file permissions or exact historical migration. A privileged legacy child was also observed to **escape cgroup v1** successfully; its physical containment remains NO-GO.

## Three actual two-boot USB/rescue failures in guest ext4 images

On every scenario the first guest verified all 5 SHA256 frozen originals, performed **fdatasync(file) + fsync(parent directory)**, fsynced `stage=2` after replacing 2 of 5 scripts, and then QEMU was **host SIGKILLed**. The second guest booted **without the simulated Entware USB**:

| Scenario | Second boot outcome | Evidence |
| --- | --- | --- |
| `baseline` with intact rescue virtual disk | Restored all **5/5** bytes | Journal survived SIGKILL; verified original SHA |
| `rescue-missing` with empty substitute rescue virtual disk | **Fail closed, zero active-file writes** | Missing archive SHA; host dump+cmp of all 5 active files |
| `rescue-absent` with rescue block device completely detached | **Fail closed, zero active-file writes** | Only active disk attached; guest refuses to proceed when expected second virtio device absent; host dump+cmp of all 5 files |

The last case is a real missing **virtual** block device, but not a real Keenetic physical USB removal. Kernel 4.9 Debian filesystems, virtual ext4 images and host QEMU SIGKILL **do not** prove flash hardware power loss or an independent physical guardian.

## Versioned deliverables and immutable evidence

- `xray/lab/rc10_fullvm_runner.sh`, `xray/lab/rc10_fullvm_init`, `xray/lab/rc10_guest_socket_cap_probe.c`, `xray/lab/rc10_guest_guardian_generation_cas.c`.
- `xray/lab/rc10_native_tproxy_minimal_caps.sh`.
- `.github/workflows/xray-v30-rc10-linux49.yml`, `.github/workflows/xray-v30-rc10-native-cap-tproxy.yml`.
- `xray/staging/v30-rc10-linux49-capability-tproxy-cas-rescue-review.json`: 7 exact source Git blobs + exact Debian package and `vmlinuz` SHA256 and official Xray SHA256, CI IDs, stage evidence and all physical release NO-GOs.
- `tests/test_xray_v30_rc10_linux49_release.py`: immutable source SHA and release gate tests.
- Artifacts: Linux4.9 [**13051156793**](https://github.com/ment2/keenetic-vpn/actions/runs/41224765496), native network namespaces [**13051425498**](https://github.com/ment2/keenetic-vpn/actions/runs/41224152158), expire Nov 14, 2026.

## Exact remaining physical blockers / release decision

1. Debian **x86_64 Linux 4.9** is not the vendor's **MIPS32LE Linux `4.9-ndm-5`**, even if both use 4.9 code. No production-like MIPS kernel TPROXY packet test with exact inherited capabilities or full DNS/IPv6 no-leak.
2. Real actual **privileged** descendants can escape cgroup v1, and live S97/S98/S99/wifi/watchdog/cron processes have **not been fully inventoried or fenced**. No guarantee of no `killall` or stale writer during real cutover.
3. Real physical USB-independent rescue guardian and boot hook have **not been demonstrated**. All storage and reboot tests occurred only in disposable QEMU images; no physical unplug or power-loss attestation.
4. Production Xray binary/config PID/SHA and kernel capabilities have not been refreshed by permitted read-only evidence; no new router jobs were submitted or blocked reads bypassed.
5. No exact physical-file owner approval, production restore/rollback, or DNS/IPv6/kill-switch/TCP+UDP end-to-end validation.

**Disposition: RC10 DISPOSABLE LAB PASS, HARD_NO_GO_PRODUCTION.** All code changes were strictly confined to `feature/xray-v30-stable-tcp-ingress-lab-20261031`. Production, Cloudflare, firewall, routes, cron, kill-switch, main and snapshot unchanged; no router jobs, merge, deploy or live trial.
