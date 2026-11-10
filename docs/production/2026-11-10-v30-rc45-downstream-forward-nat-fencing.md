# RC45: downstream FORWARD, NAT and process fencing

Date: 2026-11-10. Repo ment2/keenetic-vpn, branch feature/xray-v30-stable-tcp-ingress-lab-20261031.

## Existing read-only job

Job 144ff49c-6f3a-46f8-b58f-2ff983961839 returned done, exit_code=0. It was not resubmitted.

- FORWARD policy DROP and two consecutive jumps to XRAY_KS_HOME (previous job).
- _NDM_ACL_IN, _NDM_ACL_OUT, _NDM_IPSEC_FORWARD empty.
- _NDM_VPN_FORWARD calls SSTP/IKE1/IKE2 forward chains.
- _NDM_FORWARD calls _NDM_HOTSPOT_FWD, then _NDM_UPNP_FORWARD_SYS conditionally.
- _NDM_SL_FORWARD sends NEW packets toward eth3, apcli0, apclii0 to _NDM_SL_PROTECT.
- _NDM_MASQ calls _NDM_MASQ_BYPASS first; then Home 192.168.1.0/24 non-br0 traffic with ndmmark 0x4/0x0 is MASQUERADEd.
- XRAY_KS_HOME: six duplicate destination 192.168.0.0/16 RETURN, seven duplicate Home br0 DROP.
- PID/start_ticks/PPID: watcher 719/4471/1; S98 757/4495/1; S99 769/4501/1; watchdog 776/4506/1; memory bridge 751/4483/1; assistant 906/5009/769.

## Direct WAN policy

Owner allows client direct WAN during maintenance and temporary rollback, but not firewall/service changes. -I XRAY_KS_HOME 1 ... -j RETURN does not guarantee direct WAN: after return, processing proceeds through system FORWARD chains and default DROP. -j ACCEPT at the beginning of the kill-switch would bypass system policy and must not be proposed as safe. No new NAT rule should be added without inspecting _NDM_MASQ_BYPASS and mark/path. Do not remove duplicated pre-existing rules as part of this transaction.

## Fencing and rollback

S98 stop only signals its pidfile process and does not wait for in-flight child. Watchdog can invoke S97 killall xray; kill-switch watcher invokes reassertion every 15s. S99 kills direct children, not all descendants. Cron updater stages pending config. Before changes, require fresh boot ID, PID/start_ticks, process tree, chain counters, Xray/config hashes, backup and independent management access. Fence all competing writers without blanket killall or indiscriminate chain flush; preserve non-Xray services. Roll back only transaction-owned changes and verify intended post-maintenance VPN policy. During maintenance/rollback, direct WAN is allowed, but management path must remain recoverable.

## Remaining read-only gate

Job 8886b0b6-e3ed-4566-a0bb-81d2412a1a0d queued once to inspect _NDM_HOTSPOT_FWD, _NDM_UPNP_FORWARD_SYS, _NDM_SL_PROTECT, VPN forward subchains, _NDM_MASQ_BYPASS, and simulated Home client route lookup. Poll only, do not resubmit.

**HARD NO-GO for physical changes.** No firewall, routes, modules, cron or services changed. No full executable write command approved yet.
