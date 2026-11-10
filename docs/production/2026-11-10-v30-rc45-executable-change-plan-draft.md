# RC45 controlled downtime — executable command candidates and unresolved gates

Status **DRAFT / HARD NO-GO**. Owner authorizes VPN outage, session loss, direct WAN during maintenance/temporary rollback, **not** physical changes.

Confirmed: S97 stop uses `killall xray`; watchdog checks SOCKS5 every 30s and restarts S97; S98 every 60s may flush/rebuild XRAY_WIFI; kill-switch watcher reasserts XRAY_KS_HOME every 15s; cron updater stages config.pending.json without restart every 15m. XRAY_KS_HOME has 13 duplicate RETURN/DROP rules; FORWARD two duplicate jumps and DROP policy. Kernel 4.9-ndm-5; TPROXY target not registered; XRAY_WIFI nine RETURN, zero TPROXY; mark 0x40000000/0x40000000 -> table100 local lo. Boot ID 17cc872c-36cb-4411-899e-9eec5f3155c9. Same-USB backup verified, off-USB deferred.

Queued read-only file reads (do not resubmit): S99 `5a54acea-bd62-41e7-9f96-9349e5db1d01`, S98 `1ad616bd-7af0-45ab-88a8-a3bc745fd069`, kill-switch watcher `9e2bcdd6-7d75-4b52-9431-f615df3754e5`.

## Proposed exact commands — DO NOT EXECUTE

Temporary Home direct WAN candidate, **not guaranteed sufficient** because later FORWARD chains/policy DROP may still block:
```sh
/opt/sbin/iptables -I XRAY_KS_HOME 1 -i br0 -s 192.168.1.0/24 -j RETURN
```
Inverse **only if uniquely owned by this transaction**:
```sh
/opt/sbin/iptables -D XRAY_KS_HOME -i br0 -s 192.168.1.0/24 -j RETURN
```
TPROXY **only after registered module, fenced S98 and verified chain**:
```sh
/opt/sbin/iptables -t mangle -A XRAY_WIFI -p tcp -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000
/opt/sbin/iptables -t mangle -A XRAY_WIFI -p udp -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000
```
Inverse **only for transaction-owned unique rules**:
```sh
/opt/sbin/iptables -t mangle -D XRAY_WIFI -p udp -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000
/opt/sbin/iptables -t mangle -D XRAY_WIFI -p tcp -j TPROXY --on-port 12345 --tproxy-mark 0x40000000/0x40000000
```

## Blockers
Full S99 and S98 control-flow ownership and descendants; safe bounded fencing and respawn prevention for S97/S98/watchdog/cron; verified Home WAN packet path/NAT; module-load compatibility/registration; exact candidate config SHA and atomic rollback; live recovery witnesses. Do not fabricate stop, insmod or config commands. Never blanket flush, killall or remove existing duplicate rules. Require fresh boot/PID/start_ticks and chain identities and separate approval of exact literal commands before each physical phase.

Acceptance: planned direct WAN allowed only during maintenance/rollback; after cutover verify designated VPN egress, SOCKS5, TCP/UDP, DNS, IPv4/IPv6, OpenAI and supervisor stability. Roll back transaction-owned changes and restore original config and intended final routing, with management access maintained.