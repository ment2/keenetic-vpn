# Xray v30 RC45: verified same-USB production backup (2026-11-10)

## Decision
Owner approved same-USB recovery for the current phase and deferred independent off-USB/Home Assistant backup. This is an accepted limitation, **not** equivalent resilience against USB loss. Do not claim RC45 hardware/recovery acceptance is complete.

## Executed operation
Keenetic job `7f128810-e84e-4240-9631-096a10d5cab3` returned `done`, `exit_code=0`:

```
/opt/backups/xray-v30-prechange-20261110-161607/xray-production.tar.gz: OK
BACKUP_VERIFIED=/opt/backups/xray-v30-prechange-20261110-161607
```

The owner explicitly approved the exact archive operation. Command created `/opt/backups/xray-v30-prechange-20261110-161607/` on `/dev/sda1` (ext4, mounted at `/opt`), and archived `etc/xray`, `etc/init.d`, `bin/xray*`, and `sbin/xray`. It generated `SHA256SUMS`, ran `gzip -t`, and successfully checked `sha256sum -c SHA256SUMS`. This verifies compressed archive integrity, **not** restoration or completeness against every privileged writer. Archive contents can include production VPN credentials; never commit or upload archive/config to GitHub or ChatGPT Library.

## Baseline and restrictions
- Kernel `4.9-ndm-5`; `xt_TPROXY.ko` vermagic `4.9-ndm-5 SMP mod_unload MIPS32_R2 32BIT`, `depends=` empty, aliases `ipt_TPROXY`, `ip6t_TPROXY`; module not loaded/registered.
- `xt_socket.ko` file exists. TPROXY rules are absent and iptables logs show `No chain/target/match by that name`.
- Home Assistant `192.168.0.169` TCP/22 and TCP/8123 reachable; SSH authentication not proven: Dropbear SSH to HA failed before authentication with `No matching algo mac c->s`. Home Assistant off-USB route deferred.
- No firewall, route, Xray process, kernel module, or production service changes performed in this phase. Only the USB backup write was approved and executed.
- No GitHub Actions runs; GitHub feature branch only.

## Next gates
1. Read-only review of actual archive manifest, hash and sizes without exposing credentials.
2. Prepare and owner-approve a recovery procedure using the USB archive. Do not extract over live files or stop services without separate approval.
3. Separately approve and validate any `xt_TPROXY` activation, legacy S97/S98/S99/watchdog/cron fencing, fail-closed and rollback before two-rule TPROXY modification.
4. Physical acceptance remains NO-GO pending these gates; USB-only backup cannot recover from loss of `/dev/sda1`.
