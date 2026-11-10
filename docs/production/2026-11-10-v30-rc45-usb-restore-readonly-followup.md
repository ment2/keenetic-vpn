# RC45: USB restore read-only follow-up, timeout and successful bounded checks

Date: 2026-11-10. Repository ment2/keenetic-vpn. Branch feature/xray-v30-stable-tcp-ingress-lab-20261031.

## Existing job results (no resubmission)
- `b58e34b5-e7bd-4ebc-8055-4b75848ff6c3`: `status=done`, `exit_code=124`, `output=execution_timeout`. This job attempted a per-file byte comparison by repeatedly extracting archive members. The timeout is NOT evidence of mismatch or corruption. Full file-by-file byte comparison remains **unverified**.
- `cc4f5b6d-610f-4a90-bbc1-2a62355057ce`: `status=done`, `exit_code=0`, read-only output:
```
=== HASH ===
/opt/backups/xray-v30-prechange-20261110-161607/xray-production.tar.gz: OK
=== FILE COUNTS ===
99
=== CRITICAL MODES ===
-rw-------    1 root     root          6615 Oct 30 03:16 /opt/backups/xray-v30-prechange-20261110-161607/restore-test/etc/xray/config.json
-rwxr-xr-x    1 root     root      33751197 Mar 15  2026 /opt/backups/xray-v30-prechange-20261110-161607/restore-test/sbin/xray
=== DISK ===
Filesystem                Size      Used Available Use% Mounted on
/dev/sda1                 3.7G    247.2M      3.4G   7% /tmp/mnt/394dd440-83e6-44ea-9b35-4f3f27f3d272
READ_ONLY_CHECK_DONE
```
The count 99 is the number of regular files in the checked extracted directory tree; it is not the number of archive entries (104), and does not prove byte-for-byte equivalence.

## Established recovery evidence
Archive `/opt/backups/xray-v30-prechange-20261110-161607/xray-production.tar.gz` verified SHA256/gzip, earlier isolated extraction returned success. Restored config is nonempty with mode 0600, restored binary is executable. Archive and extracted files are on same USB, not independent disaster recovery. No live restoration or rollback has occurred.

## Restrictions and next gates
No production files, services, firewall, routes, kernel modules, cron or Xray processes were modified by the read-only jobs. No new writes to Keenetic without separately approved exact command. Next diagnostics should avoid repeated decompression of 9.9MB archive per member; compare metadata or a single-pass manifest if truly needed. Before physical TPROXY change, kernel target registration, legacy writer fencing, fail-closed and rollback gates remain open. NO-GO for cutover. Never upload archive/config/credentials to GitHub or Library.
