# RC45: verified ELF module metadata and process start ticks

Date: 2026-11-10. Repository: ment2/keenetic-vpn. Branch: feature/xray-v30-stable-tcp-ingress-lab-20261031.

## Existing job result

Keenetic Mobile job `9ed973ad-8ae3-4156-80a4-9c149f8a56e0` was polled without resubmission and returned `status=done`, `exit_code=0`.

Read-only `strings` extraction from existing ELF module files:

| File | aliases | depends | vermagic |
|---|---|---|---|
| `/lib/modules/4.9-ndm-5/xt_TPROXY.ko` | `ip6t_TPROXY`, `ipt_TPROXY` | empty | `4.9-ndm-5 SMP mod_unload MIPS32_R2 32BIT` |
| `/lib/modules/4.9-ndm-5/xt_socket.ko` | `ip6t_socket`, `ipt_socket` | empty | `4.9-ndm-5 SMP mod_unload MIPS32_R2 32BIT` |

These metadata indicate a vendor-kernel ABI match and no declared module dependencies, but do NOT prove safe module activation, missing external requirements, actual target registration or packet interception. `TPROXY` did not appear in `/proc/net/ip_tables_targets` in the same job.

Read-only `/proc/PID/stat` start-tick witnesses:

| Process | PID | start_ticks |
|---|---:|---:|
| Kill-switch watcher | 719 | 4471 |
| S98 Wi-Fi watcher | 757 | 4495 |
| Xray watchdog | 776 | 4506 |
| Xray | 815 | 4570 |

Earlier observed boot ID: `17cc872c-36cb-4411-899e-9eec5f3155c9`. It was NOT re-read by this job. PID/start_ticks are a historical snapshot, not permission to signal a process. Refresh boot ID, PID/start_ticks, descendants and firewall baseline before any approved maintenance.

## RC45 decision

**HARD NO-GO** for physical module load, firewall rule changes, service fencing, first API cutover. Nine RETURN exclusions and zero TPROXY rules were directly verified in a previous read-only job. Same-USB archive integrity and isolated extraction succeeded; off-USB disaster recovery was deferred. No writes or restarts occurred in this job. Any Keenetic write requires an exact command and separate owner approval.
