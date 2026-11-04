# RC39 SSH bridge audit: pinned HA host, Dropbear MAC mismatch

Date: 2026-11-04, branch feature/xray-v30-stable-tcp-ingress-lab-20261031.

## Confirmed HA terminal evidence

- SSH account `menttwo` uid 1000, `PermitRootLogin no`, `PubkeyAuthentication yes`, `StrictModes yes`, AuthorizedKeysFile `/etc/ssh/authorized_keys /root/.ssh/authorized_keys`.
- HA SSH server ED25519 public key `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAICFWgmmf5hu+ALdNaQ6iufzK2wbIrEoeXYxsWlLFh8B+` has independently computed fingerprint `SHA256:JDvdGtVYmfsv0mrhlAGLV8DtMueXK2EaR6kS/YXVgFE`, matching HA terminal ssh-keygen output. No private key was retrieved.
- User installed one restricted public key into HA /etc/ssh/authorized_keys for router source IP 192.168.0.135. It has `from=`, `restrict` and a forced echo test command; this is **only a connectivity test**, not yet a file-transfer authorization. The public key's private part resides at `/opt/etc/vpn-monitor/ha-backup/id_ed25519`, mode 0600.
- HA backup target /backup/keenetic-rescue created mode 0700, root owned. Archive contents have not been transferred. Need a properly scoped HA login and permission delegation for eventual write; user menttwo uid1000 cannot write to root-owned 0700 target by default.

## Router read-only + low-impact pinned-host test

- Router job 87235da4... confirmed SSH private key exists mode 0600. /opt/bin/ssh is Dropbear 2025.89 (symlink to /opt/sbin/dropbear), **not OpenSSH**.
- Router copied exactly HA's independently validated ED25519 public host key into its own `/opt/root/.ssh/known_hosts`; it used `StrictHostKeyChecking=yes` and no trust bypass.
- Pinned SSH test `1323ae33-fa9a-480d-8e5a-c2667465533e` reached Home Assistant but failed **before authorization** with `No matching algo mac c->s`; test exit 1. `ConnectTimeout` is not a recognized Dropbear option and was ignored. No shell or file copy executed.
- `/usr/bin/ssh` and `/bin/ssh` absent. Entware package list has `openssh-client 10.2_p1-1`, not installed. Its package installation would potentially collide with existing `/opt/bin/ssh` symlink, so **not installed**. Local package metadata lacks visible SHA256 and shows download over HTTP; avoid unverified execution and don't weaken HA sshd algorithms merely to connect.
- Earlier RC39 CI 768/768 PASS at d7bdf231; no CI for the actual HA SSH transport. Fresh physical recovery remains HARD NO-GO.

## Next safe choice
Use a separately verified OpenSSH client isolated from Dropbear, or configure a HA-initiated SFTP/SSH pull after independently pinning the Keenetic SSH host key and limited access on router. Do not loosen Home Assistant MAC suites, disable SSH host checking, disclose keys, copy plaintext VPN secrets, modify S97/watchdog or restart Xray. The restricted test key is not yet authorized for backup writes; exact transfer mechanism and encryption must be independently proven.
