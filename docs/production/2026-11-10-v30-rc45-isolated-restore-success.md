# Xray v30 RC45: isolated USB restore test succeeded

Date: 2026-11-10. Repository: ment2/keenetic-vpn; branch: feature/xray-v30-stable-tcp-ingress-lab-20261031.

## Verified execution
Owner separately approved the exact isolated restore command. Existing Keenetic task `cc4fd70f-f695-47e2-96ca-b79de7c788ae` was polled without resubmission and returned `status=done`, `exit_code=0`:

```
/opt/backups/xray-v30-prechange-20261110-161607/xray-production.tar.gz: OK
RESTORE_TEST_OK=/opt/backups/xray-v30-prechange-20261110-161607/restore-test
```

Executed command checked the archive using `sha256sum -c SHA256SUMS` and `gzip -t`, extracted with `tar -xzpf` into an isolated directory on the same USB, then checked that `restore-test/etc/xray/config.json` exists and is nonempty and `restore-test/sbin/xray` is executable. `set -eu` and exit code zero establish that all commands succeeded. No output disclosed the config contents or credentials.

## Backup baseline
Archive: `/opt/backups/xray-v30-prechange-20261110-161607/xray-production.tar.gz` (~9.9 MB). Earlier independent inventory job `3f039846-734f-4376-9335-976a4bc0faf3` reported 104 archive entries: 33 under `etc/xray`, 20 under `etc/init.d`, 50 under `bin/xray*`, 1 under `sbin/xray`; SHA256 and gzip passed.

## Scope and limitations
This test proves the archive could be extracted to a separate USB directory and two selected restored files passed existence/executable checks. It is NOT a live restore, rollback acceptance, comparison of all restored files to production, or off-USB disaster recovery. Same USB `/dev/sda1` remains a single point of failure. Do not publish archive/config/secrets to GitHub or ChatGPT Library.

The approved command did not change live Xray files, firewall, routes, modules, services or processes. No new Keenetic writes are authorized. Before any new write, show the exact command and obtain separate explicit owner approval. RC45 physical TPROXY activation and production cutover remain NO-GO pending independent gates (module activation, legacy writer fencing, rollback/no-leak verification).
