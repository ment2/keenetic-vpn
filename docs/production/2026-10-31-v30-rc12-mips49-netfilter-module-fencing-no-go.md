# RC12 MIPS32LE Linux 4.9 netfilter archive discovery and privileged legacy fencing

Date: 2026-10-31. Scope: `ment2/keenetic-vpn`, branch `feature/xray-v30-stable-tcp-ingress-lab-20261031` only. Prior checkpoint RC11 `92d1357b6f4256564ac6b216f6e118850abe6e61`.

## Boundary and hypothesis

The real MIPS full-system QEMU Malta guest in RC11 verified kernel `4.9.0-13-4kc-malta`, `CAP_NET_RAW`, actual transparent TCP/UDP sockets, authentic Xray 26.2.6, CAS 8x3, and a **successful privileged cgroup v1 escape**; see [RC11](2026-10-31-v30-rc11-mips49-real-fullsystem-legacy-root-escape-no-go.md).

RC12 inventories the **exact SHA256-pinned archived Debian MIPS32LE 4.9 kernel package**, its `xt_TPROXY`, `xt_socket`, `iptable_mangle`, `ip_tables` and `x_tables` components and other supporting modules; `modinfo` and `readelf` only parse bytes. A matching `.ko` (or built-in `=y`) proves only a **static artifact candidate**. It cannot prove MIPS packet routing, a loaded module, an enabled NIC, `fwmark`, a policy rule or Xray delivery.

At the RC11 endpoint the QEMU guest used `-net none`, and no guest MIPS iptables, nftables or route table was installed. Thus the TCP and UDP packet-path tests have **not** run on MIPS Linux4.9, regardless of archive module inventory outcome. Native x86 TPROXY CI is not MIPS proof.

## Safety contract and adversarial gating

`xray/lab/rc12_privileged_fencing_packet_gate.py` rejects each missing acknowledgment for **all seven** original S97/S98/S99/watchdog/Wi-Fi/cron spawning surfaces; tests individually mutate **every actor × every acknowledgment**. It also rejects root cgroup escape, unknown root writer, detached `fork/setsid/exec` descendants, ambiguous boot ID/PID/start-ticks/socket inodes, generation CAS and PREPARED-crash replay, untested packet counters/direct fallback/DNS+IPv6, and unproven independent physical power/USB/rescue rollback. A fully green **synthetic** fixture remains `OFFLINE_REVIEW_CANDIDATE_ONLY` and can never grant deployment.

The **observed root cgroup v1 escape is a positive HARD NO-GO witness**. Cooperation via `flock` is insufficient to fence privileged legacy scripts that ignore the lock. Until independent enforcement and exact root spawner inventory is physically demonstrated, no cutover can be made safe merely by more PID scans.

## CI and decision

- Disposable read-only archive inspection workflow: `.github/workflows/xray-v30-rc12-mips49-module-discovery.yml`.
- Additional offline mutation tests: `tests/test_xray_v30_rc12_netfilter_inventory.py`, `tests/test_xray_v30_rc12_privileged_fencing.py`.
- Archived Debian package and `vmlinux` exact SHA256 hard-coded from RC11 and verified before extraction/inspection.
- CI inventory results to be recorded only after a completed workflow; a green **discovery** workflow is not TCP/UDP packet-path success.

**HARD_NO_GO_PRODUCTION**. To close the lab gap, an isolated future experiment must load verified same-kernel MIPS modules, configure guest-only NIC+netfilter+fwmark+policy routing, show actual TCP/UDP packet bytes/counters and no bypass after killing the directly owned Xray child, then test IPv6/DNS with no-leak. Physical vendor `4.9-ndm-5`, privileged legacy process fencing, and power/USB-independent boot guardian remain separate hard acceptance gates.

No router jobs; no production/main/snapshot/Cloudflare/firewall/routes/cron/merge/deploy/live trial.
