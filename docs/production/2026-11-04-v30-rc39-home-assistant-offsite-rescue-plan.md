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
