# RC45: physical TPROXY capability read-only findings and bounded two-rule change request

Date: 2026-11-07. Repository: ment2/keenetic-vpn. Branch ONLY: feature/xray-v30-stable-tcp-ingress-lab-20261031. Source checkpoint before this note: 84387e026d528f3235ee9a80e8133fa6c71fcab4.

**CURRENT DECISION: NO-GO FOR PHYSICAL CHANGE OR FIRST API CUTOVER. THIS FILE IS A PROPOSED CHANGE REQUEST, NOT EXECUTION PERMISSION.**

The owner permits a first migration with VPN interruption and existing TCP/UDP session loss. Full preservation of historical Xray activeConn is NOT a prerequisite. However an independent rollback and continuing fail-closed policy are required. No production, main, snapshot, Cloudflare, firewall/route/cron write, module load, Xray restart, merge or deploy has occurred in RC45.

## 1. Fresh Keenetic Mobile evidence, no repeated jobs

Authorized only read-only diagnostics. Connected owner-admin state was remote_enabled=true and scopes diagnostic/exec/read_file/write_file, but capability does not imply approval to change the physical router.

Unique router job receipts:
- e3bf54dc-8192-44fc-b2f8-b01a6b5055d7: diagnostic result done / exit 124, output_limit_reached; NO facts or success imputed from it and no resubmission.
- 6d3dffce-1b70-45fb-8371-26748b4643bd: done exit 0; actual S96/S98/watchdog/cron, their PID and root child snapshots, known_hosts, HA LAN reachability, mount status.
- 16ac1ce6-2c56-4315-a82b-da2aaecc98e4: done exit 0; xtables 1.4.21 backend, exact nine RETURN chain SHA, missing registered kernel target, module and userspace path inventory.
- 79e2e3dd-6de7-4010-964d-955adaa7ae13: done exit 0; bounded tail/error-category classification of EXISTING logs, no raw log or secret contents.
- cbdd63c8-c21c-4a71-8480-cd0f0d2a6b73: done exit 0; read-only filesystem search and TPROXY help output, NO actual target test or kernel write.
- df8bc985-3cab-4c3e-a1ff-c0663a2b8599: done exit 0; existing xt_TPROXY.ko byte digest and module index presence, noninteractive pinned-host-key SSH authentication attempt to HA; NO transfer or restore.

No duplicate task submissions. No write_file, exec of iptables mutation, insmod/modprobe, file staging, service signal, restart or live trial.

## 2. Physical netfilter target is NOT available at time of inspection

The actual /opt/sbin/iptables binary resolves to /opt/sbin/xtables-multi. The reported iptables version is **1.4.21**. iptables-save and iptables-restore also point at the same xtables-multi; the -V argument to those subcommands is NOT reliably a version command (iptables-save returned a rule dump), so do not pretend their options were validated.

Read-only actual chain:
- XRAY_WIFI: one declaration, exactly nine RETURN exclusions and ZERO TPROXY; full listing SHA256 **44f3d783cae72cb3987133c3f84abac389f1f1e4d91b98bafeafd04f1a5c3891**, still equal to the RC43 baseline and exact RC44 versioned-source reconstruction.
- PREROUTING: two jumps to XRAY_WIFI.
- FORWARD: two jumps to XRAY_KS_HOME. These are NOT removed by this repair.
- No TPROXY target found in /proc/net/ip_tables_targets and no xt_TPROXY module found in /proc/modules at check time. This means it is NOT currently observed loaded/registered, not that the kernel could never load it.
- Typical libxt_TPROXY.so and libipt_TPROXY.so paths were absent; the actual read-only userspace command /opt/sbin/iptables -t mangle -j TPROXY -h succeeded with TPROXY --on-port and --tproxy-mark help. Thus **userspace extension parsing is available**; missing typical shared-object paths are NOT proof of missing userspace support.
- Actual kernel module file EXISTS at /lib/modules/4.9-ndm-5/xt_TPROXY.ko, size **9336 bytes**, SHA256 **2e78816ca7115768200c46ac83fa8301a1912139d72baa22005a8d2220b99423**. Its dependency metadata files modules.dep, modules.builtin and modules.softdep were absent in that scanned kernel module directory; automatic loading and dependency closure cannot be inferred. No module load was attempted.

Existing /opt/var/log/xray-wifi.log was 211412 bytes. In its bounded last 24576 bytes, 535 lines were sampled and **534 matched a fixed whitelist of missing chain/target/match error patterns**. The source script has no checked failure after append of TPROXY and can return exit 0 even with both target appends rejected, as proven by RC44 pinned-shell failure injection. The exact physical failing syscall, errno, whether root module loading failed and complete log context were not independently captured: do not attribute these counts to a specific syscall without evidence. The kill-switch and Xray watchdog bounded log samples had zero matching error categories. No log contents or credentials were printed.

## 3. Actual supervisors and scheduling that can race a change

Live read-only PIDs/start_ticks:
- S96 kill-switch watcher 719 / 4471, with child; root pidfile valid.
- S98 Wi-Fi TPROXY repair watcher 757 / 4495, with child; root pidfile valid.
- Xray watchdog 776 / 4506, with child; root pidfile valid.
- Root cron contains one Xray-related entry, every **15 minutes**, involving xray-safe-hourly.sh and an updater lock; staging-only hourly updater can spawn a second short-lived Xray for config test.
- /opt/tmp/xray-fc-guard-enabled ABSENT, so that optional cron recover branch was not enabled in the snapshot.
- These PIDs are ephemeral evidence, NOT future target selectors. S98 runs the original flush-and-rebuild path every 60 seconds if the TPROXY target appears absent. The S96 watcher runs xray-ks-home.sh every 15 seconds and its first-FORWARD-rule test can cause duplicate XRAY_KS_HOME jumps. The regular Xray watchdog may call legacy S97 global killall on port loss.
- Root descendant quiescing and cross-process kernel write fencing remain unproven. Merely SIGSTOP of S98 parent is insufficient; no physical stop occurred in this check.

## 4. Recovery reality

- Keenetic /opt is writable USB, around 3554 MiB free. / is read-only (0 writable), /tmp is volatile around 123 MiB.
- Existing original router archive was previously SHA-verified 11/11 and its original permissions require restoration for nine entries. It does NOT survive USB failure by itself.
- HA at 192.168.0.169 answers TCP22 with OpenSSH_10.3 and 8123 is reachable from Keenetic.
- /opt/root/.ssh/known_hosts EXISTS (unlike the older RC39 state), but a strict, noninteractive root SSH read-only probe using this pinned hosts file failed rc=1 without any remote command output; error classified only as network_or_other. Do NOT claim authenticated access, verified remote /backup mount, encrypted archive transfer, restore or SSH trust acceptance. No StrictHostKeyChecking bypass, no key read or publication.
- Off-USB independent recovery remains unproven. No encrypted transfer or restore was performed.

## 5. Exact proposed change request, in two SEPARATELY APPROVED phases

**CR45-A: kernel target support / recovery prerequisite, HOLD.** Before any physical write:
1. Obtain fresh exact boot ID, kernel/module SHA and current target registration; independently check xt_TPROXY.ko dependencies and mechanism for kernel target registration on Keenetic OS 4.9-ndm-5, preferably with vendor documentation and a matching disposable MIPS49 test. Presence of a .ko file and userland help is not proof it can safely be loaded.
2. Verify a separate off-USB encrypted backup with pinned HA SSH host key, successful noninteractive account access, expected remote persistent storage, archive SHA256 and restore-to-disposable-location with preserved original modes. Local phone Termius LAN recovery must work without VPN.
3. Produce a separate reviewed change proposal for any module loading or dependency enablement (if needed), including failure/rollback and boot persistence. **No approval to modprobe/insmod or to permit auto-loading has been granted by this request.** Even an iptables append could trigger auto-loading; that side effect MUST be within the explicit future approval or operation must abort.
4. Prove a window in which all concurrent S98, S97, S99/watchdog, cron and root descendants cannot replace chain or kill Xray, without turning off FORWARD DROP or the independent kill switch. Re-check process identities and the current chain immediately before the operation.

**CR45-B: minimum TWO-RULE TPROXY append, HOLD until CR45-A and separate owner signoff.** Exact intended operation, for review ONLY, once the old kernel has an actual working registered TPROXY target, no existing TPROXY in chain, all nine exclusions match, S98 writer is safely quiesced and independent rollback has been proven:

    /opt/sbin/iptables -t mangle -A XRAY_WIFI -p tcp -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000
    /opt/sbin/iptables -t mangle -A XRAY_WIFI -p udp -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000

These are two separate operations and NOT atomically safe by themselves. **They are not a script to run today.** Unlike the disposable Ubuntu CI, the real device uses iptables 1.4.21 and its installed iptables-restore --noflush support was NOT independently verified, so do not transplant the CI batch unreviewed. Use exact pre-change full mangle/filter and process/boot snapshot, private only, plus per-protocol command exit and readback. If the first append succeeds and the second fails, trigger approved rollback of ONLY the verified transaction-owned TCP rule, not a broad flush.

**Proposed exact inverse selectors, NOT AUTHORIZED until protected from concurrent S98 writes:**

    /opt/sbin/iptables -t mangle -D XRAY_WIFI -p udp -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000
    /opt/sbin/iptables -t mangle -D XRAY_WIFI -p tcp -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000

Perform ONLY applicable inverse selectors actually inserted in this transaction. Without a private before/after ruleset and an exclusive writer guarantee, an identical selector might belong to another actor and must not be blindly deleted. No global killall, no S97 restart, no PREROUTING/FORWARD delete, no old Xray config mutation, no independent killswitch disable, no module unload simply to revert the rule addition. Actual module activation needs its OWN rollback design.

## 6. Exact verification and abort matrix

**Pre-write GO tests:**
- xt_TPROXY dependencies independently established, kernel target usable on exact vendor kernel and separate authorization for module activation/auto-load if necessary;
- Home Assistant off-USB recovery independently proven; backup verified; local SSH working;
- current XRAY_WIFI is EXACT nine exclusions + zero TPROXY, with same source hash, no unaccounted entries;
- exact two PREROUTING br0 source/protocol jumps, unique 10808 SOCKS and 12345 TCP/UDP Xray socket owner, current PID/start_ticks/boot ID, firewall mark 0x40000000/table100 local lo;
- IPv4 FORWARD DROP and first XRAY_KS_HOME, IPv6 FORWARD DROP, DNS IPv6 and default route fail-closed baseline, WAN direct path disabled;
- competing S98/cron/root children safely quiesced, no asynchronous S97 restart/candidate Xray race. Maintain independent fail-closed mechanism and recovery.

**Post-write acceptance:**
- 9 original RETURN entries still in original order, exactly one new TPROXY TCP and one new TPROXY UDP, expected port 12345 and mark, unchanged PREROUTING/FORWARD/killswitch/policy route and original Xray PID/start ticks;
- actual Wi-Fi-source TCP and UDP traverses Xray to a controlled external destination, observed by real TPROXY per-protocol counter deltas plus **end-to-end application results**, not counters alone; SOCKS through VPN and OpenAI reachability HTTP 401 without API token as appropriate;
- independent IPv4 and IPv6 leak tests from Wi-Fi clients, DNS egress and unintended direct WAN routes, including an intentional VPN-down fail-closed scenario only in separately approved safe maintenance conditions. No secret endpoints/credentials in GitHub logs;
- survives at least two 60-second S98 cycles with S98 restored under a corrected supervision/error policy; old flush-and-rebuild implementation must not silently erase the new rules; S96 watchdog remains active, duplicate FORWARD not modified by this CR;
- no Xray or other required service crash, local LAN administration persists.

**Abort or rollback on:** any module target missing, new chain hash drift, concurrent writer or root child, failed packet probe, absent UDP/TCP target, unexpected rule count/order, any direct IPv4/IPv6/DNS leak, broken backup/restore, failing SSH recovery, or watchdog restart. Prefer leaving fail-closed and an explicit owner local recovery step over unsafely opening direct WAN access.

## 7. Release evidence and truthful limits

RC44 real native disposable Linux CI 42347863653 **SUCCESS 19/19**: actual transparent TCP and UDP sockets received synthetic packets after precisely two TPROXY rules, kernel counters positive; exact original rule semantics/order restored on rollback and packets failed closed. RC44 offline CI 42347863507 **SUCCESS 845/845**. These are NOT Keenetic-vendor or physical module activation tests.

**RC45 physical read-only checks: completed for target and supervisor evidence, but kernel dependency/activation, HA SSH authenticated recovery, actual packet acceptance and safe quiesce NOT done.** Therefore **NO-GO for real module loading, firewall repair and first API cutover**. No module or firewall writes, router restarts, cron edits, Xray signals, Cloudflare operations, production/main/snapshot merge or deploy occurred.

Next actionable request: explicitly review an independent HA rescue and vendor module-dependency activation plan (read-only first), followed by exact separate approvals for module action (if needed) and two-rule firewall transaction. First API migration remains a controlled service interruption, not a seamless UDP exercise.
