# Keenetic Xray v30: first API cutover canary, autonomous rollback and exact commands for review

Date 2026-10-31. Repository `ment2/keenetic-vpn`, branch `feature/xray-v30-stable-tcp-ingress-lab-20261031`. **STATE: candidate code / synthetic tests; NOT INSTALLED or EXECUTED on production.** Owner has explicitly approved preparing and testing but has NOT approved the exact production cutover command.

## Proven live inventory and local access

- Owner confirmed local Termius `root@192.168.1.1:222` SSH succeeds via Keenetic Wi-Fi with phone VPN disabled, command `echo LOCAL_RECOVERY_OK` succeeded. This is a manually tested out-of-band recovery channel, provided the router remains booted and LAN reachable.
- Live read-only job `a7fb1802-02ee-41d8-96f9-8845b539f32f`, done/exit 0: primary Xray PID 13546, start_ticks 100216734, active config SHA256 `66d074f32fffbf4a251576c8297714e9647174546e9e73e5bf27cf2768efe6d7`, backup manifest SHA256 `f27c336f66f1bbb9ef22a82f7e8aa84f80f9bee808b3a87abf6a5372e79d5c62`.
- Legacy watchdog PID **32713**, start ticks **61575997**, pidfile `/opt/var/run/xray-watchdog.pid`; S98 Wi-Fi repair PID **24097**, start ticks **60711544**, pidfile `/opt/var/run/xray-wifi.pid`. Their actual shell cmdlines and script SHA were checked, without reading secrets. These PID values are a snapshot, NOT eternal references.
- Verified source SHA256: `S97xray` `87ea1dc13a9be95d57c0595d7a7f13b03fe97bd56ab1f144a3c94d57cc588d5d`, `S98xray-wifi` `6742e5e7f2a2bd41b85e9975371e7c46e66f0cfc6f5f843bf2c5dc1434c53601`, `S99xray-watchdog` `e8423e15ed2cf4d3662e5725d27d6e58bd08bbdd807b47fcabe30391ac4c738b`, watchdog shell `dddcc1d324e30b91df041378645ada869a18b4d35f2842383e5d319fc859e08`, Wi-Fi rules shell `ead5de5555aaab1170a140ca3d41ea546330a99ba873b1961bee536bc12780ef`.
- Read-only job `c14d136a-4acb-4a14-b76e-516b37b3d2c4`, done/exit 0: `iptables -S FORWARD` begins with `-P FORWARD DROP`, `-A FORWARD -j XRAY_KS_HOME` as FIRST rule; both TCP and UDP `XRAY_WIFI` rules target `12345` with `--tproxy-mark 0x40000000/0x40000000`; IPv6 FORWARD policy DROP. A default drop is NOT a full no-leak audit.
- Old config, binary and shell sources are preserved root-only under `/opt/var/backups/xray-v30-precutover-20261031-1045Z`; 11 files + 5 network-rule snapshots; integrity and offline Xray config parse verified previously. No actual production restore has been performed.

## Prepared code (DO NOT DEPLOY without exact command approval)

- `xray/lab/v30_first_migration_transaction.py`: durable synthetic transaction (generation CAS, PID/start_ticks, backup/local SSH guard, watchdog and S98 fence, old listener stop, candidate protocol/API readiness, rollback and recovery). Never runs OS signals or router operations.
- `xray/lab/v30_autonomous_guard_rehearsal.py`: detached synthetic guardian in a **separate OS process**; persists a journal, survives parent process return; positive fixture becomes `restored`, negative fixture becomes `blocked`. Fake fixture does NOT demonstrate actual process signal/port restoration.
- `xray/staging/v30_first_cutover_canary.py`: DRAFT **real router executable** for a **15-second API-enabled ingress trial** with automatic return to old Xray. It is **not installed**, not approved and not proven safe on Keenetic. Pins all critical live code SHA256, original config, binary and backup; requires explicit `--accept-network-interruption` plus expected old PID/start ticks/hash; serializes JSON state in root-only `/opt/var/run/xray-v30-canary/` with file and directory fsync. **No production config rewrite, init rewrite, firewall modification, route change, cron change, or permanent promotion.**
  - Before stopping legacy Xray it launches a separate session-independent guardian (90-second wall+monotonic bounded deadline), verifies its PID/start_ticks, SIGSTOP-fences exactly the known old watchdog **and S98 Wi-Fi repair** with PID/start_ticks/cmdline checks, and confirms both are truly stopped.
  - It then SIGTERM-signals ONLY the verified legacy Xray, without global `killall` or SIGKILL escalation; starts an API-enabled candidate from a private copy of the old config on the original ports 10808 and 12345, with API bound to 127.0.0.1:19090. The active `config.json` is NEVER overwritten.
  - Canaries check TCP SOCKS listener ownership, TCP+UDP 12345 ownership, local API TCP port, `https://api.openai.com/v1/models` HTTP 401 through SOCKS, both TPROXY iptables rules, fwmark/table100, first IPv4 kill-switch rule, IPv6 FORWARD DROP, watchdog and S98 fence ownership. They DO NOT prove genuine gRPC API behavior, full TPROXY TCP/UDP packet delivery through candidate, actual VPN Telegram or DNS/IPv6 leak absence.
  - After 15 seconds (or any known error) it attempts PID-scoped candidate termination, restores the **original config** process on original listeners, re-tests the old SOCKS VPN, then resumes frozen watchdog and S98, all with process-identity checks. Detached guardian triggers equivalent restoration at 90s if control process disappears. If restoration is not fully proven, journal enters `blocked`, kernel fail-closed must remain and owner uses local Termius; guard will not silently retry.
  - Safety caveat: only one independent guardian process. Unexpected guardian crash, rapid reboot, power loss, kernel faults, unexpected Xray process, race with out-of-band S99/S98 restart or lost USB are NOT robustly recovered by this lab test. **Therefore this canary is NOT production-approved even with green offline CI.**

## Exact command bundle for separate review (NONE of these commands have been executed)

The next gate is **explicit approval of writing the reviewed Python file onto the router** as `/opt/bin/v30_first_cutover_canary.py` with mode `0700`, plus independent checksum/readback. The source in private GitHub must not be downloaded with an exposed token. The MCP `write_file` operation requires separate approval of the **exact absolute path and complete source**. Merely requesting this runbook does not approve that upload.

Once the approved exact source is installed and its hash verified, the following are the **exact proposed invocation forms**. The PID/start_ticks are pinned to the Oct 31 snapshot; **if the process identities or SHA have changed, these commands MUST fail**. No script currently exists at this on-router path.

**1. Read-only command, safe after installation:**
```sh
/opt/bin/python3 /opt/bin/v30_first_cutover_canary.py --plan --expected-old-pid 13546 --expected-old-ticks 100216734 --expected-config-sha 66d074f32fffbf4a251576c8297714e9647174546e9e73e5bf27cf2768efe6d7
```
Expected success: `READ_ONLY_PRECHECK_OK`; shows watchdog and S98 PID/start ticks. Otherwise stop. This stage checks the immutable backup, source hashes, active binary, both TPROXY protocols and kill-switch.

**2. DISRUPTIVE 15-second trial, requires a DIFFERENT, separate owner's exact-command approval:**
```sh
/opt/bin/python3 /opt/bin/v30_first_cutover_canary.py --trial --expected-old-pid 13546 --expected-old-ticks 100216734 --expected-config-sha 66d074f32fffbf4a251576c8297714e9647174546e9e73e5bf27cf2768efe6d7 --accept-network-interruption
```
This command must **not** be run now. It SIGSTOP-pauses the legacy watchdog and S98, SIGTERM-stops the running Xray, starts the temporary API Xray on the same TCP/UDP listener ports and automatically tries to restore old Xray. Current phone sessions can be broken. No guaranteed upper bound on recovery under failure. This is only a **canary**; it does not permanently migrate the production service or implement final dynamic pool management.

**3. Immediate manual emergency rollback in Termius over local Wi-Fi (only after the program and journal exist):**
```sh
/opt/bin/python3 /opt/bin/v30_first_cutover_canary.py --rollback
```
On a `blocked` journal requiring an explicitly authorized manual retry:
```sh
/opt/bin/python3 /opt/bin/v30_first_cutover_canary.py --rollback --retry-blocked
```
Never use `/opt/etc/init.d/S97xray restart` or any global `killall xray`: it can kill the new and old processes and defeat scoped recovery. If a PID/identity gate refuses an action, do not override it or copy a stale literal PID into `kill`; inspect locally and recover intentionally.

**4. Read-only operator verification after canary:**
```sh
sha256sum /opt/etc/xray/config.json /opt/var/backups/xray-v30-precutover-20261031-1045Z/manifest.json
netstat -lnptu | grep -E '(:10808|:12345)'
ip rule show
ip route show table 100
/opt/sbin/iptables -S FORWARD | head -n 3
```
Expected: original config SHA restored and a single original-config Xray owning both TCP+UDP ingress. Compare PID/start_ticks from `/proc` and inspect guardian journal securely. Any unclear ownership => block and use local SSH.

## Independent validation and blockers

- CI `41196749756`: **SUCCESS**, 216/216 synthetic/offline tests. CI `41196944984`: **SUCCESS**, 222/222 incl detached guardian in a separate process, restored and blocked cases. CI `41197095295`: **SUCCESS** with independent guard shell invocations in workflow. Subsequent CI is reported separately from the branch head.
- These tests verify only models, process control under mocks, source syntax and replay. They **do not** authorize on-router stop of real Xray.
- Before any real trial we should perform an owner-approved upload with full content hash and local **non-disruptive `--plan`**, then a separate non-live drill of actual signals/guard against harmless auxiliary processes on Keenetic to prove guardian survival when remote session disappears. Full TPROXY UDP, DNS/IPv6 path and reliable one-time permanent API migration require later additional tests and permanent watchdog replacement.
- `xray-v30-first-cutover-canary.py` should NOT be placed in the production `S97xray` init/cron. It is a temporary trial runner only.
- Historical incident: process PID 15329 appeared during prior offline config verification and exited; never signal based on that stale PID.

**Conclusion: source and approval commands prepared. Production cutover NOT RUN. GitHub main/snapshot, router's working Xray, firewall, watchdog, cron, routes and kill-switch unchanged by this phase.**
