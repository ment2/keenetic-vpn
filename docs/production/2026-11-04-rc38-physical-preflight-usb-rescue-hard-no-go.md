# RC38 physical preflight: backup resides on USB, independent rescue absent

Date: 2026-11-04. Existing project `ment2/keenetic-vpn`, branch `feature/xray-v30-stable-tcp-ingress-lab-20261031`.
This is a read-only hardware inventory, NOT an approved production cutover, deployment, watchdog update, or physical recovery acceptance. Owner permits a temporary VPN outage, but physical rollback remains unverified.

## Exact read-only Keenetic tasks

- `0e352908-927b-47f0-b910-a3ee2fc5be6f`: done exit 0. Production Xray still PID 13546; watchdog PID 32713; kernel 4.9-ndm-5. On-disk live SHA256 `66d074f32fffbf4a251576c8297714e9647174546e9e73e5bf27cf2768efe6d7`, seven VLESS tags `vpn01,vpn02,vpn04,vpn05,vpn06,vpn07,vpn09`. Pending SHA256 `77c809e962a5966323504c0d613c0b8297cd36f1213ec284876b1f3c80bdfccd`, five tags `vpn01,vpn02,vpn04,vpn05,vpn09`. Legacy S97, S98, S99, watchdog SHA256 obtained without modifying files.
- `3f149ab6-fe0f-420a-8512-86c790346563`: done exit 0. Backup directory `/opt/var/backups/xray-v30-precutover-20261031-1045Z` exists, containing private manifest and 5 network/routing snapshot files plus `opt/` subtree. **/opt is mounted on /dev/sda1**; / is `/dev/root`, /tmp is tmpfs. Thus the backup in /opt is not independent of USB failure.
- `a735fe28-ba3c-4b8c-ae46-d4a5815e1bc5`: done exit 0. Manifest created `2026-10-31T10:45:27Z`; 11 archived file entries. `/root` and `/etc` are on a different device from /opt, but physical persistence, mount integrity and independent boot rescue have not been proven. No configured rescue directory located at `/root/xray-v30-rescue`, `/etc/xray-v30-rescue` or `/data/xray-v30-rescue`.
- `93d116a6-bc3b-4c58-b774-f86fdad90ea4`: done exit 0. All 11 backup entries match expected SHA256 and size. No raw config/credentials disclosed.
- `41e89031-64b5-4fda-8a6c-d1e5a0c5be16`: done exit 0. 2 of 11 archived file permission modes match manifest's original_mode; 9 differ. This may reflect intentionally private archival permissions; **must restore original modes when recovering**. The archived bytes are valid; the difference is a restore-procedure requirement, not evidence of corruption.

## Release decision

**HARD_NO_GO_PRODUCTION** remains for any automated first-migration or auto-apply script. Reasons:

1. No independently proven off-USB rescue, booted without USB and validated after power loss.
2. Existing S97 globally `killall xray`; watchdog can invoke it. Existing privileged S97/S98/S99/watchdog/cron descendants not independently fenced.
3. Current legacy production Xray has no API. RC36 pinned source proves full old UDP session ownership cannot be inferred from conntrack after expiration; seamless migration remains unproven.
4. Need original permission-mode restoration and manifest-verified rollback, local SSH, SOCKS5, TPROXY TCP/UDP, DNS/IPv6 no-leak and fail-closed acceptance.
5. Owner permission for a brief outage does not prove explicit acceptance of losing established sessions, and does not waive 1–4.

## Safe next stage

- Work only in existing feature branch and disposable lab; design a full recovery bundle and test manifest mode restoration and mismatch fail-closed.
- First hardware operation, if separately reviewed, should be a non-destructive creation of a separate off-USB rescue package with exact manifest verification, on-device mount/persistence proof and local recovery procedure; **do not assume merely writing to /root proves USB-independent boot recovery**. Real physical USB-unplug/reboot would require user intervention.
- No `killall`, S97 restart, config replacement, cron/firewall/route edits, Xray deployment or main/snapshot merge occurred.
- Previous RC37 offline CI 41814237742 SUCCESS 752/752 at SHA 52f3a042. Attempts to add a further process-control test through the GitHub connector were safety-blocked; do not retry/bypass that block. This preflight is read-only and independent of it.


## Additional independent media check and CI (same day)

- Router read-only job `480a176c-1de4-4325-be24-accef42b5c76`, done exit 0: `/`, `/root` and `/etc` belong to a **read-only** root filesystem (`/dev/root`, 0 free writable bytes). `/opt` is a **writable USB mount** (`/dev/sda1`, approximately 3.73 GB available); `/tmp` is volatile tmpfs (approximately 130 MB free). Therefore **none of these existing writable mounts provides a durable, independent, non-USB rescue**. Do not attempt to write to read-only root or claim `/tmp` survives reboot.
- `xray/lab/rc38_rescue_archive_audit.py` added as strictly read-only archive verifier with safe root-relative path constraints, symlink denial, SHA256/size verification and original-mode restoration requirements. It never restores files or authorizes production.
- `tests/test_xray_v30_rc38_rescue_archive_audit.py`: 10 dedicated negative/positive tests. Full GitHub Actions source-contracts **762/762 SUCCESS**, run https://github.com/ment2/keenetic-vpn/actions/runs/41815955189 at exact source SHA `460decc23552d9efbe9bb7a8be880de00f513a96` (job 126526627458). This is runner-side CI, **not physical USB-loss testing**.
- User action is needed to establish an independent and recoverable off-USB rescue path (e.g., separate reliable storage with tested local restoration). There is no safe automatic deployment path on the verified current mounts. Still `HARD_NO_GO_PRODUCTION`.
