# Xray v30 RC45: USB backup verified inventory and recovery gate

Date: 2026-11-10. Repo: ment2/keenetic-vpn, feature/xray-v30-stable-tcp-ingress-lab-20261031.

## Verified read-only result
Existing Keenetic job `3f039846-734f-4376-9335-976a4bc0faf3` completed with exit_code 0. No resubmission.

- Archive: `/opt/backups/xray-v30-prechange-20261110-161607/xray-production.tar.gz` on `/dev/sda1` (the same USB backing `/opt`).
- Archive size: 9.9 MiB (as reported by `ls -lh`, rounded).
- `SHA256SUMS` size: 137 bytes.
- `tar -tzf` yielded 104 entries: `etc/xray/` 33; `etc/init.d/` 20; `bin/xray*` 50; `sbin/xray` 1.
- `sha256sum -c SHA256SUMS`: `xray-production.tar.gz: OK`.
- `gzip -t`: `GZIP_OK`.

This verifies archive readability and integrity, not successful restoration, independent USB recovery, absence of sensitive contents, or protection from loss of `/dev/sda1`.

## Owner decision and restrictions
Owner approved same-USB backup as the current recovery medium, deferring Home Assistant/off-USB. No new Keenetic writes without showing the exact command and receiving separate explicit approval. No changes to firewall, routes, running Xray, kernel modules, or production services. No GitHub Actions.

## Recovery procedure: draft, not executed
1. Confirm USB filesystem is mounted at `/opt`, archive exists, and SSH management access works. Preserve current fail-closed rules.
2. Verify `sha256sum -c SHA256SUMS` and `gzip -t` before any restore.
3. Inventory target paths and compare to archive manifest; archive includes executable and init scripts and may contain secrets. Do not publish archive or its config to GitHub/Library.
4. Restore only the individually approved target files, preserving permissions/ownership and a separate snapshot of displaced files. Never run `tar -xzf` over the whole live `/opt` blindly.
5. Independently authorize any service stop/restart or kernel module action. Verify local management, Xray sockets, firewall fail-closed, TCP/UDP VPN and no-leak; rollback on any failure.

## Remaining RC45 blockers
`xt_TPROXY.ko` has kernel-matching vermagic and empty declared `depends`, but is not loaded/registered. Missing live TPROXY rules; legacy writer fencing not proven. A same-USB archive is not a verified recovery mechanism against USB failure. Physical cutover remains NO-GO until separately approved gates and rollback are accepted.
