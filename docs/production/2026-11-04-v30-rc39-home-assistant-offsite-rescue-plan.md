# RC39: Home Assistant as independent Keenetic rescue storage (2026-11-04)

Repository: `ment2/keenetic-vpn`; ONLY `feature/xray-v30-stable-tcp-ingress-lab-20261031`. The owner agreed to use separate Home Assistant host for disaster-recovery backup. **Nothing has been copied or deployed yet.**

## Network observations, from read-only router tasks
- Destination Home Assistant: `192.168.0.169`. TCP port **22 responds with `SSH-2.0-OpenSSH_10.3`**; 8123 HTTP and 1883 MQTT also reachable. Ports 445/139 SMB, 873 rsync, 8080 WebDAV and 22222 HA host SSH were refused.
- `/opt/bin/ssh` and `/opt/bin/scp` available on Keenetic. `openssl`, `age`, `gpg`, `sftp`, Python `cryptography` and `PyNaCl` unavailable. Do not implement improvised cryptography or transmit plain config data over MQTT, HTTP or ChatGPT.
- Existing 11-file archive `/opt/var/backups/xray-v30-precutover-20261031-1045Z` verified 11/11 SHA256/size. Nine archived file modes differ from original manifest modes and require explicit mode restoration.
- `/opt` is writable USB `/dev/sda1`; root `/dev/root` read-only; `/tmp` volatile. Merely copying within the Keenetic does not create an off-USB recovery bundle.
- HA advanced SSH add-on likely provides the TCP 22 listener, but the listener's identity, SSH host-key trust, login credentials and mounted `/backup` permissions are **not yet verified**. Do not guess that port 22 gives access to host filesystem or that the assistant can authenticate.
- Official HA OS documentation describes a `/backup` folder and notes HA's own encrypted backup format. Those guarantees **do not automatically apply to an arbitrary Keenetic archive** placed there.

## Intended safe transfer design
1. From HA's Advanced SSH & Web Terminal, operator runs a **read-only** preflight that reports `id`, `df -h /backup`, `ls -ld /backup`, and availability of `age`/`openssl`/`gpg`, without secrets. Confirm actual persistent storage outside the router's USB and appropriate access to the backup directory.
2. Independently verify HA SSH host key fingerprint on the HA console; never use `StrictHostKeyChecking=no`.
3. Prefer SSH streaming from Keenetic to **recipient-key authenticated encryption on HA** (such as `age` with a private decryption key stored separately from both systems). Never leave a temporary plaintext archive on HA's persistent disk. Require owner-only remote account and 0700 private backup directory, no broad HA Samba share.
4. Read-only validate before transfer: tar paths must remain relative, with no symlinks or traversal; local manifest's 11 SHA256, sizes and original modes must match. Archive complete source plus necessary network/routing snapshots without leaking credentials into tools, GitHub or chat.
5. End-to-end archive digest verification after transfer and a restore-to-disposable-location rehearsal, with original modes restored. Without an actual USB-free boot plus local recovery capability, **do not represent the backup as physically accepted**.
6. Do not touch `S97xray`, watchdog, cron, Xray config, sockets, routes, firewall, Cloudflare or production until recovery and process fencing are independently proven. Existing RC36/RC37 HARD NO-GO still applies.

## RC39 offline gate
`xray/lab/rc39_ha_backup_receipt_gate.py` and `tests/test_xray_v30_rc39_ha_backup_receipt_gate.py` validate claimed SHA matching, host-key and encryption gates, but never authorize production, even if all supplied booleans are true. A model receipt is not a physical recovery proof.

## Required non-secret operator response
From HA SSH/Web Terminal, copy the output of:

```sh
printf '=== HA SSH STORAGE PREFLIGHT ===\n'
id
df -h /backup
ls -ld /backup
for x in age openssl gpg tar sha256sum python3; do command -v "$x" || true; done
```

Do not paste passwords, private SSH keys, backup contents or HA tokens. Only after this check select the exact encryption tool and transfer protocol.


## Actual HA terminal result supplied by owner

- Home Assistant Advanced SSH terminal reports `uid=0(root)`.
- `/backup` exists, owned by root, currently displayed mode `drwxr-xr-x` (0755), therefore create a **private subdirectory 0700**, rather than writing sensitive archives directly into /backup.
- Filesystem `/dev/sda8`, 116.7G total, 14.2G used, **97.7G available**, mounted in HA SSH add-on environment at `/addon_configs`. The command `df -h /backup` resolves to this filesystem. This is separate from router USB `/dev/sda1`, but its durability through host failure/reboot remains untested.
- Available executables: `/usr/bin/openssl`, `/bin/tar`, `/usr/bin/sha256sum`, `/usr/bin/python3`. `age` and `gpg` absent.
- Router read-only task `6ba43b69-97fb-4835-ba75-969b3eabdb6e`: HA TCP22/8123/1883 open, SMB445, rsync873, WebDAV8080 closed. Task `5056bbaf-a2a8-418e-869c-c06c9d31a39a`: SSH banner `SSH-2.0-OpenSSH_10.3`; router has SSH/SCP but no OpenSSL/age/cryptography.
- Router read-only task `7e8acfdb-f069-4c07-8c33-94a182c40ba0`: no existing /root/.ssh/known_hosts or /opt/root/.ssh/known_hosts. BatchMode SSH to `root@192.168.0.169` failed with exit 1, without verified host-key pinning or working login. Therefore **no transfer is authorized or possible yet**.
- Owner must independently establish SSH host-key fingerprint and authorize a dedicated public key to the HA Advanced SSH add-on (Configuration > authorized_keys; app restart if required). Never use `StrictHostKeyChecking=no` or copy secrets into chat.
- Critical: HA's Advanced SSH is itself an add-on container, so /backup visibility must be confirmed by the actual SSH login used for transfer; visible terminal path alone does not prove a remote `scp` login has identical privileges.
- Encryption on HA must be **before persistence**; OpenSSL CMS recipient encryption is a potential design, but a decryption key should be backed up separately from HA for disaster recovery. Do not silently store private decrypt keys in the same HA backup directory and claim independent availability.

Current release remains `HARD_NO_GO_PRODUCTION` for Xray cutover. No archive has been transferred.
