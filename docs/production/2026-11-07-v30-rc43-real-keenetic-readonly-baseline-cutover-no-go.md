# RC43: actual Keenetic read-only production baseline and first cutover decision

Date 2026-11-07 UTC; repository ment2/keenetic-vpn; strictly feature/xray-v30-stable-tcp-ingress-lab-20261031. This is a freshly observed router audit through the connected Keenetic Mobile plugin, not an execution of cutover. User explicitly permits service interruption and loss of established TCP/UDP sessions during first migration; session preservation and legacy activeConn inventory are not release prerequisites for this one-time maintenance operation. Safety, fail-closed and independent rollback remain prerequisites.

## Exact tool provenance, no duplicate jobs

- get_permission_status: remote_enabled=true, owner_admin_enabled=true, revision=2; no configuration changed.
- router_status diagnostic job 6e7612bb-a14c-442a-8c63-f1c45d0fa5bc, done exit 0: Keenetic ONLINE, Python 3.13.9, load (0.38,0.56,0.58), free disk approximately 3.47 GB.
- One read-only shell inventory job 94278a23-4591-4917-a0ec-754574979d96, done exit 0.
- One independent read-only backup / LAN HA reachability job 7c2a4a4f-78ad-4550-b93b-c0422c98c94c, done exit 0.
- Exactly one fresh existing, previously installed canary --plan invocation plus bounded independent rule metadata checks: job 2ae374a3-2d05-41f2-9d25-c6d31f82171b, done exit 0 for the diagnostic wrapper, but **the canary child --plan itself exited 1**. No --trial, rollback, guardian, signal or Xray restart occurred.
- One separate source-specific read-only clarification of port owner and TPROXY rules, job 2a9bc8bd-34ff-45ce-ae2c-c35c7d275929, done exit 0. This is NOT a retry of the failed --plan.
- No duplicate queue calls, no new write_file or upload to the router, no production/app/firewall/routes/cron/Cloudflare changes.

## Live Xray runtime identity (November 7 snapshot)

- Current kernel boot ID: 17cc872c-36cb-4411-899e-9eec5f3155c9. Uptime about 135236 seconds at first capture.
- Exactly one /opt/sbin/xray executable verified: PID=815, PPID=1, state=S, Linux /proc start_ticks=4570.
- The exact parser from the installed canary matched all three exclusive listeners for this PID: SOCKS TCP 127.0.0.1:10808; TPROXY TCP :::12345; TPROXY UDP :::12345.
- Real binary /opt/sbin/xray SHA256 680db07db2b5d53080bfecb8752bc830c6a890367aa3bc57d42d4660506591f2.
- Active /opt/etc/xray/config.json SHA256 66d074f32fffbf4a251576c8297714e9647174546e9e73e5bf27cf2768efe6d7, mode 0600. Same byte digest as Oct 31 known-good archival config, but API disabled. Live active VLESS tags: vpn01,vpn02,vpn04,vpn05,vpn06,vpn07,vpn09; two inbound definitions.
- Pending /opt/etc/xray/config.pending.json SHA256 79c9f45879290c70992e411e312b6c5c52b5af06070bec59e074227a902fa137, mode 0600, seven tags (same as active), API absent. This differs from the earlier five-tag pending candidate and from Nov4 pending digest 77c809e962a5966323504c0d613c0b8297cd36f1213ec284876b1f3c80bdfccd. Do NOT consider pending currently OpenAI-qualified or automatically applied. No secret endpoints/keys or raw config were collected in the report.

## Verified archived canary and supervisor sources

- Existing installed /opt/bin/v30_first_cutover_canary.py SHA256 8e57ef5054f53174a35d906d34eab073dd6d787607cb02f29d83364ae3abc203; root-only mode 0700. Matches feature-branch archived byte digest; source Git blob 495cd51581f472a9cb0a257ff7cd9f0d611dcab7. Journal state.json and guardian-ready.json absent.
- S97 init SHA 87ea1dc13a9be95d57c0595d7a7f13b03fe97bd56ab1f144a3c94d57cc588d5d. S98 init SHA 6742e5e7f2a2bd41b85e9975371e7c46e66f0cfc6f5f843bf2c5dc1434c53601. S99 watchdog init SHA e8423e15ed2cf4d3662e5725d27d6e58bd08bbdd807b47fcabe30391ac4c738b.
- Watchdog shell SHA dddfcc1d324e30b91df041378645ada869a18b4d35f2842383e5d319fc859e08. Wi-Fi rules shell SHA ead5de5555aaab1170a140ca3d41ea546330a99ba873b1961bee536bc12780ef. All match previously approved baseline; no unexpected bytes in these files.
- Currently observed cron daemon PID 677 start_ticks 4413, S98 Wi-Fi supervisor PID 757 start_ticks 4495, watchdog PID 776 start_ticks 4506; pidfiles agree. One root crontab file with 31 lines, 1 containing the word xray. Several child processes were observed at one point, but they exited before the later targeted check. They were not proved to be Xray-killing or TPROXY-writing descendants. An initial classification also matched the diagnostic shell command text itself; those matches are not trusted evidence of additional legacy actors. There is no independent, mandatory quiescing guarantee for S97/S98/S99, cron and children.

## Most important NEW hard blocker: effective ingress TPROXY rules missing

Fresh actual iptables -t mangle -S XRAY_WIFI returned success, 10 lines, target count RETURN=9, target count TPROXY=0; both expected TCP TPROXY dport 12345 and UDP TPROXY dport 12345 are ABSENT. Digest of the observed chain listing: 44f3d783cae72cb3987133c3f84abac389f1f1e4d91b98bafeafd04f1a5c3891.

The PREROUTING mangle chain has two jumps to XRAY_WIFI (duplicate), yet the destination chain contains no actual TPROXY target. The Xray TCP/UDP port 12345 is bound, but binding a port is not proof of packet interception. The missing rules therefore block evidence of functional Wi-Fi TCP/UDP TPROXY ingress. **Do not edit kernel rules without a separate exact approved change, verified backup and rollback.** This report does not prove whether there is or is not a direct Internet leak: fail-closed routing/packet tests were not performed.

iptables FORWARD policy is DROP; two identical first -A FORWARD -j XRAY_KS_HOME jumps were observed. XRAY_KS_HOME contains br0 and a DROP action. IPv6 FORWARD default policy is DROP. ip rule shows fwmark 0x40000000/0x40000000 lookup table 100; table100 contains local default dev lo. These source reads support that portions of fail-closed/policy configuration exist; they do NOT prove every IPv4/IPv6/DNS leak path is blocked. Duplicates warrant a reviewed cleanup, not unapproved physical changes.

## Why fresh --plan failed and what can be claimed

The existing installed read-only canary was invoked once with the NEW PID=815, start_ticks=4570 and still-pinned config SHA. It returned exit 1 with GateError: unexpected process or non-exclusive SOCKS/TPROXY listeners at the preflight process-owner check (before its later safe_kernel evaluation). At a separate instant, the source-identical listener checks for PID 815 all returned true and only one executable PID 815 existed. Thus a transient second Xray process or timing race is POSSIBLE, but the exact cause is not witnessed. Do not state that the canary passed. It did NOT. Do not rerun it automatically. Independently, even if the process check had passed, current iptables lacks the required TCP+UDP TPROXY rules, so its current safe_kernel checks could not be certified.

## Backup and Home Assistant: real status

- Router backup /opt/var/backups/xray-v30-precutover-20261031-1045Z exists. Its manifest SHA256 f27c336f66f1bbb9ef22a82f7e8aa84f80f9bee808b3a87abf6a5372e79d5c62 matches previous trusted archive, length 2241 bytes. All 11 archived entries again match size and SHA256, with zero file errors. Nine archived permissions differ from original_mode and require correct restoration, not blind copying.
- /opt remains writable USB with approx 3555 MB available; / is read-only, 0 writable bytes; /tmp volatile, approx 124 MB available. Current backup is NOT independent of router USB.
- From Keenetic to HA 192.168.0.169, TCP 22 OPEN (SSH banner SSH-2.0-OpenSSH_10.3), 8123 OPEN, 1883 OPEN. This is only reachability; host-key identity, authenticated encrypted transfer, private remote storage, end-to-end manifest digest, restore rehearsal and USB-free rescue have NOT been verified. No credentials or archived config were sent.

## Exact GO/NO-GO for user-approved service interruption

Decision: **NO-GO FOR TEMPORARY PRODUCTION CUTOVER NOW.** Owner permits service interruption and loss of old TCP/UDP sessions, therefore seamless activeConn inventory and kernel-freeze experiments RC40-42 are NOT the gate. Genuine blockers to address, in order:

1. Restore/verify effective Wi-Fi TPROXY **TCP and UDP** packet path on the old known-good service under a separately approved, backed-up, precisely rollbackable operation, before considering API migration. Current TPROXY rules count zero is critical. Do not silently apply firewall changes.
2. Confirm stable exclusive old-Xray PID/start-ticks/port ownership with a successful fresh preflight; investigate, rather than blindly retry, the Oct/Nov installed canary process-ownership transient failure.
3. Establish **independent** off-USB encrypted rescue and a test restore (HA TCP reachability alone is insufficient), with archived original modes and local iPhone Termius recovery reconfirmed.
4. Make an independently reviewed process/cron supervisor quiesce/rollback mechanism that does not rely solely on SIGSTOP of watchdog and S98 parent PIDs; the original S97 contains global killall and can collide with a candidate.
5. Requalify candidate VPN pool for OpenAI; do not promote the currently seven-tag pending blob on the basis of historical five-tag results. Then perform a separately approved, temporary 15-second API-enabled canary that ALWAYS returns to legacy, with real SOCKS+TPROXY packet probes, DNS/IPv6 leak and fail-closed validation, followed only later by separately reviewed permanent promotion.

Until then, production Xray, config, rules, cron, watchdog and service behavior were not intentionally modified by this audit. The read-only audit was completed and saved. No merge/deploy/live trial, no Cloudflare operations.

## Commit and baseline

Checked upstream feature HEAD before document update: 0c2c46cf4a05617dc12d66e68fb490d2fa2ad79e. The RC43 CI already succeeded at 42344891097 (7/7) and 42344841429 (826/826) for offline read-only helper. Those CI runs did not perform live router checks; real read-only jobs above are the source of current evidence. More GitHub/Library reports may summarize only these verified facts.
