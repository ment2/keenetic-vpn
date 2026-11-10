# RC45: FORWARD/NAT and direct-WAN gates

Read-only Keenetic job `ed491d37-c13f-4984-bb27-c1db3c8d60b1` done, exit 0, not resubmitted.

- FORWARD policy DROP; two `-j XRAY_KS_HOME` before system ACL/VPN/FORWARD chains.
- NAT POSTROUTING uses `_NDM_MASQ`, which includes `-s 192.168.1.0/24 ! -o br0 -m ndmmark --ndmmark 0x4/0x0 -j MASQUERADE`. Presence does not prove packet acceptance or mark compatibility.
- Router underlay route `1.1.1.1 via 192.168.0.1 dev apclii0 src 192.168.0.135` observed earlier.
- PID snapshot: kill-switch watcher 719, S98 757, S99 769, Xray watchdog 776, Telegram memory bridge 751, assistant 906. Verify boot ID/start ticks before actions.

Owner permits direct WAN during maintenance/rollback, **not** firewall/service writes. Temporary `RETURN` candidate is insufficient alone because FORWARD policy DROP and downstream system chains may block. Direct ACCEPT inside XRAY_KS_HOME is unsafe because it bypasses system policy. Do not add NAT rules without packet/mark proof. Candidate only, **NOT AUTHORIZED**:

```sh
/opt/sbin/iptables -I XRAY_KS_HOME 1 -i br0 -s 192.168.1.0/24 -j RETURN
```

Conditional inverse only for transaction-owned unique match:

```sh
/opt/sbin/iptables -D XRAY_KS_HOME -i br0 -s 192.168.1.0/24 -j RETURN
```

Fencing: identify boot/PID/start ticks and descendants, stop S98 in-flight rebuild, watchdog->S97 killall, kill-switch watcher, config cron/respawners. S99 stops only direct children. Require verified management and rollback, then separately approved exact commands for Xray stop/start, TPROXY registration/rules and config swap. Session loss and temporary direct WAN allowed; after cutover verify Home TCP/UDP/DNS/IPv6 and assigned VPN egress. Restore normal policy and all supervisors. No blanket flush/killall.

Pending **read-only** job `144ff49c-6f3a-46f8-b58f-2ff983961839` to inspect downstream FORWARD and process start ticks; poll only, never resubmit. **HARD NO-GO** for physical changes.
