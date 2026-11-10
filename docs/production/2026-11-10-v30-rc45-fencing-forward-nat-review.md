# RC45: verified fencing and pending FORWARD/NAT

Existing read-only jobs returned done without resubmission:

- S99 `5a54acea-bd62-41e7-9f96-9349e5db1d01`: `stop` kills direct children (`pgrep -P`) then parent, not recursively validated descendants; start waits for SOCKS5 port 10808 and loops restarting assistant.py.
- S98 `1ad616bd-7af0-45ab-88a8-a3bc745fd069`: every 60 seconds checks mangle PREROUTING TCP/UDP jumps, XRAY_WIFI TPROXY and table100 local route, then calls xray-wifi-rules.sh if any missing. Stop signals pidfile PID but does not wait for active child scripts.
- Kill-switch watcher `9e2bcdd6-7d75-4b52-9431-f615df3754e5`: every 15 seconds invokes xray-ks-home.sh, no built-in stop in inspected script.

Owner permits direct WAN for clients during maintenance and temporary rollback, not router modifications. Temporary exception candidate (NOT APPROVED):

```sh
/opt/sbin/iptables -I XRAY_KS_HOME 1 -i br0 -s 192.168.1.0/24 -j RETURN
```

Inverse, only if transaction-owned and unique:

```sh
/opt/sbin/iptables -D XRAY_KS_HOME -i br0 -s 192.168.1.0/24 -j RETURN
```

**RETURN is not ACCEPT:** downstream FORWARD chains and policy DROP may still block. NAT for br0 to apclii0 must be checked before deciding exact WAN exception. S98/watchdog/kill-switch watcher/cron need identity-fenced controls with no active descendants; S97 killall xray must not be invoked blindly. TPROXY candidate rules and inverses remain in preceding RC45 change request; no permission to execute. Same-USB backup verified, off-USB deferred. Read-only FORWARD/NAT job queued `ed491d37-c13f-4984-bb27-c1db3c8d60b1`; poll only, do not resubmit. HARD NO-GO pending those results and exact verified process controls. No live writes performed.
