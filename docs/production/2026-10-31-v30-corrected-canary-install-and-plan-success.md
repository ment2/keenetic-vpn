# Keenetic Xray v30: corrected canary installed, hash validated, only --plan passed

Date **2026-10-31**, tested live on the user's existing Keenetic. Repo `ment2/keenetic-vpn`, **only** branch `feature/xray-v30-stable-tcp-ingress-lab-20261031`. This report is **not** production cutover/rollback authorization.

## Exact consent and source provenance

Owner explicitly consented to replacing exactly `/opt/bin/v30_first_cutover_canary.py` with complete corrected GitHub source `xray/staging/v30_first_cutover_canary.py`:
- **Git blob SHA** `495cd51581f472a9cb0a257ff7cd9f0d611dcab7`
- **SHA256** `8e57ef5054f53174a35d906d34eab073dd6d787607cb02f29d83364ae3abc203`
- **22,208 bytes**, trailing newline; source's corrected watchdog literal `dddfcc1d324e30b91df041378645ada869a18b4d35f2842383e5d319fc859e08`.
- Authenticated GitHub source was fetched afresh and exact Git blob SHA/byte length/expected watchdog literal checked **before** issuing a single router write. Full source presented to owner prior to replacing.
- GitHub Actions **[41200967162](https://github.com/ment2/keenetic-vpn/actions/runs/41200967162)**: SUCCESS 253/253 offline tests incl signed source `sha256sum -c`; not live router proof.

Exact restricted approval permitted: **one** source replacement, chmod 0700, independent on-device SHA256/mode validation, and **one exact --plan** invocation. Explicitly no `--trial`, `--rollback`, `--guardian`, no Xray/watchdog/S98 process signals, no change to active Xray configuration, kernel firewall/routes/cron/kill-switch, Cloudflare, main, snapshot or deployment; no merge.

## Single submitted router jobs and outcomes

1. **Replace file once** via Keenetic Mobile `write_file`, job `4d425b63-94f4-4a3d-8b94-bb10296bd6e1`: **done / exit_code=0**; `written=true`, `backup_created=true`; Agent returned exact expected new SHA256 `8e57ef5054f53174a35d906d34eab073dd6d787607cb02f29d83364ae3abc203`. The prior installed canary was backed up by the agent. Original root-only Xray pre-cutover backup `/opt/var/backups/xray-v30-precutover-20261031-1045Z` remained untouched.
2. **chmod and SHA verification** job `56916d8d-1f4c-4a43-a83e-b373dea7a2c1` executed `chmod 0700` successfully and printed the correct SHA256, but **exit_code=1** because the validation command `stat -c` is unsupported by BusyBox stat on this Keenetic (`invalid option -- 'c'`). This was a **verification-command compatibility error**, not file/hash drift. The script did not touch network or processes.
3. **Independent Python read-only verification**, job `ac54698d-21cc-49eb-b6e1-ad944b6d642c`: **done / exit_code=0**; returned `MODE=0o700`, `OWNER=0:0`, `SIZE=22208`, `SHA256=8e57ef5054f53174a35d906d34eab073dd6d787607cb02f29d83364ae3abc203`, and `XRAY_V30_CORRECTED_SHA_MODE_OK`. This used `os.stat` and `hashlib.sha256`, avoiding BusyBox `stat -c`. It did not repeat the write/chmod.
4. **Only once: the EXACT approved read-only preflight** job `5d0f3748-d9f2-4e88-a7d5-daa4e63b9ecd`: **done / exit_code=0**. Invoked:
```sh
/opt/bin/python3 /opt/bin/v30_first_cutover_canary.py --plan --expected-old-pid 13546 --expected-old-ticks 100216734 --expected-config-sha 66d074f32fffbf4a251576c8297714e9647174546e9e73e5bf27cf2768efe6d7
```
Exact output:
```text
READ_ONLY_PRECHECK_OK
WATCHDOG_PID_TICKS=32713:61575997
S98_PID_TICKS=24097:60711544
GUARD_NOT_ARMED; NO_CHANGE; NO_APPROVAL
```

## What passed and what remains unproven

Passed **live read-only** checking: expected Xray PID 13546/start_ticks 100216734, exclusive original SOCKS+TPROXY TCP/UDP port ownership, original config and Xray binary SHA, all 11 pre-cutover backup files and root-only manifest SHA, pinned init/watchdog/S98/wifi hashes, firewall TPROXY TCP and UDP 12345/fwmark, first FORWARD fail-closed chain, policy route table 100, IPv6 FORWARD DROP, watchdog PID/start_ticks 32713:61575997 and S98 24097:60711544. No contents/secrets exposed. This resolves previous false “watchdog drift” failure caused by the 63-character embedded SHA.

**Not tested or authorized**: `--trial`, `--rollback`, `--guardian`; stopping/replacing old Xray, child process supervision, real TPROXY TCP/UDP flow handoff, DNS/IPv6 no-leak end-to-end, Telegram paths, power-cycle recovery, guardian crash/failover, permanent API migration. `READ_ONLY_PRECHECK_OK` is not full network migration readiness.

## Next gate

**Installation stage is COMPLETE.** Do not repeat any of the four jobs. The corrected script is on Keenetic root-only mode 0700 with exact validated hash. For any disruptive first cutover, separate exact command approval with risk explanation, rigorous autonomous-rollback proof, watcher/S98 race guards, local independent Termius rescue access and new live guard checks is mandatory. No production cutover has occurred.

**Disposition:** success within explicitly authorized scope. Live Xray, firewall, routes, cron, kill-switch, Cloudflare, GitHub main/snapshot remain untouched. No merge or deploy.
