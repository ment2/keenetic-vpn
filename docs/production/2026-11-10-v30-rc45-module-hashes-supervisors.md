# RC45: physical module hashes, missing indexes and live supervisor inventory

Date: 2026-11-10. Branch: feature/xray-v30-stable-tcp-ingress-lab-20261031.

Existing read-only Keenetic job `b3efdd27-54a1-42f0-8107-a42722b71a88` completed `done`, `exit_code=0`. No resubmission.

## Module files and SHA256
- `/lib/modules/4.9-ndm-5/xt_TPROXY.ko`: 9336 bytes, root:root mode 0644, SHA256 `2e78816ca7115768200c46ac83fa8301a1912139d72baa22005a8d2220b99423` (same as earlier verified RC45 reading).
- `/lib/modules/4.9-ndm-5/xt_socket.ko`: 9464 bytes, root:root mode 0644, SHA256 `5adeed9ef033444f2b64c4ee4f3d78c3b4a28d85825e82dba754cbfb15c72d60`.
- Absent: `modules.dep`, `modules.builtin`, `modules.softdep` at `/lib/modules/4.9-ndm-5/`. This does not prove either module can or cannot load; dependency closure and target registration remain untested.

## Read-only process snapshot
```
677  root cron -s
719  root /opt/bin/sh /opt/bin/xray-ks-home-watch.sh
757  root /opt/bin/sh /opt/etc/init.d/S98xray-wifi start
776  root /opt/bin/sh /opt/bin/xray-watchdog
815  root /opt/sbin/xray run -config /opt/etc/xray/config.json
9620 root cron -s
```
PIDs are ephemeral and cannot be used for later signaling without fresh PID/start_ticks and boot identity.

Earlier read-only job `65ac984c-e99d-4b25-a74c-00f95b151788` confirmed kernel `4.9-ndm-5`, boot ID `17cc872c-36cb-4411-899e-9eec5f3155c9`, nine XRAY_WIFI RETURN exclusions and zero TPROXY; target absent in `/proc/net/ip_tables_targets` and `xt_TPROXY` absent in `/proc/modules`.

**HARD NO-GO**: no module activation, firewall write, cron/service change, cutover, or privileged writer fencing authorized. Same-USB recovery is verified only for isolated extraction, not live rollback or off-USB disaster recovery. Continue read-only.